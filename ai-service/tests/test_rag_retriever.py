"""
2026-09-02: Internal RAG observability 회귀 테스트.

rag_retriever.retrieve()가 semantic_raw/semantic_selected 로그를 남기고,
apply_retrieval_rule() 전후로 원본 Document 리스트(개수/순서/score)가
로깅 때문에 바뀌지 않는지 확인한다.

실제 PostgreSQL 연결이나 BGE 모델 로딩은 하지 않는다 - get_connection()과
encode_query()를 mock으로 대체한다.
"""

import contextlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# rag_retriever.py는 모듈 최상단에서 torch를 import한다(bge_runtime_config()의
# torch.cuda.is_available() 때문). 실제 임베딩 요청이 없는 이 테스트에서는
# 최소한의 더미 모듈로 대체한다 - 다른 테스트 파일(test_retrieval_orchestrator.py)
# 과 동일한 패턴, 이 파일이 끝나면 원상복구한다.
_installed_torch_stub = False

Document = None
RetrieveRequest = None
RetrieveResponse = None
retrieve = None
retrieve_scoped_lexical = None
document_log_summary = None


def setUpModule():
    global _installed_torch_stub
    global Document, RetrieveRequest, RetrieveResponse
    global retrieve, retrieve_scoped_lexical, document_log_summary

    if "torch" not in sys.modules:
        torch_stub = types.ModuleType("torch")
        torch_stub.cuda = types.SimpleNamespace(is_available=lambda: False)
        sys.modules["torch"] = torch_stub
        _installed_torch_stub = True

    from app.schemas.models import Document as _Document
    from app.schemas.models import RetrieveRequest as _RetrieveRequest
    from app.schemas.models import RetrieveResponse as _RetrieveResponse
    from app.services.retrieval.rag_retriever import (
        retrieve as _retrieve,
        retrieve_scoped_lexical as _retrieve_scoped_lexical,
        document_log_summary as _document_log_summary,
    )

    Document = _Document
    RetrieveRequest = _RetrieveRequest
    RetrieveResponse = _RetrieveResponse
    retrieve = _retrieve
    retrieve_scoped_lexical = _retrieve_scoped_lexical
    document_log_summary = _document_log_summary


def tearDownModule():
    if _installed_torch_stub:
        sys.modules.pop("torch", None)


def _fake_connection(rows):
    """get_connection()이 반환하는 context manager를 흉내낸다."""
    cursor = MagicMock()
    cursor.execute.return_value = None
    cursor.fetchall.return_value = rows
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False

    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False

    return conn


_SAMPLE_ROWS = [
    (1, 101, 0, "문서A", "OTHER", None, "문서A의 0번째 청크 본문입니다." * 5, 0.91),
    (1, 102, 1, "문서A", "OTHER", None, "문서A의 1번째 청크 본문입니다." * 5, 0.77),
    (2, 201, 0, "문서B", "OTHER", None, "문서B의 0번째 청크 본문입니다." * 5, 0.44),
    (2, 202, 1, "문서B", "OTHER", None, "문서B의 1번째 청크 본문입니다." * 5, 0.31),
    (3, 301, 0, "문서C", "OTHER", None, "문서C의 0번째 청크 본문입니다." * 5, 0.12),
]


class RetrieveObservabilityLogTest(unittest.TestCase):
    def setUp(self):
        self._encode_patch = patch(
            "app.services.retrieval.rag_retriever.encode_query",
            return_value=__import__("numpy").zeros(4),
        )
        self._encode_patch.start()

        self._conn_patch = patch(
            "app.services.retrieval.rag_retriever.get_connection",
            return_value=_fake_connection(_SAMPLE_ROWS),
        )
        self._conn_patch.start()

    def tearDown(self):
        self._encode_patch.stop()
        self._conn_patch.stop()

    def test_a_raw_and_selected_logs_both_appear_when_raw_exceeds_selected(self):
        # min_score=0.50(document_ids 없음)이라 0.44/0.31/0.12인 3개는
        # apply_retrieval_rule()에서 걸러진다 - raw(5)가 selected(2)보다
        # 많은 케이스.
        req = RetrieveRequest(
            query="문서 요약해줘",
            owner_user_id=1,
            top_k=3,
            document_ids=[],
        )

        with self._capture_stdout() as out:
            result = retrieve(req)

        log = out.getvalue()
        self.assertIn("[RAG] semantic_raw count=5", log)
        self.assertIn("[RAG] semantic_selected count=2", log)
        self.assertEqual(len(result.documents), 2)

    def test_b_returned_documents_match_existing_retrieval_rule_result(self):
        # apply_retrieval_rule()의 실제 필터링/정렬 결과(로깅 없이 직접
        # 호출한 것)와, retrieve()가 로깅과 함께 반환한 결과가 완전히
        # 같아야 한다 - 로깅이 순서/score/개수에 영향을 주면 안 된다.
        from app.services.retrieval.retrieval_rule import apply_retrieval_rule

        raw_documents = [
            Document(
                document_id=row[0],
                chunk_id=row[1],
                chunk_index=row[2],
                title=row[3],
                document_type=row[4] or "OTHER",
                description=row[5],
                content=row[6],
                score=float(row[7]),
            )
            for row in _SAMPLE_ROWS
        ]

        expected = apply_retrieval_rule(
            raw_documents,
            top_k=3,
            min_score=0.50,
            max_chunks_per_document=2,
        )

        req = RetrieveRequest(
            query="문서 요약해줘",
            owner_user_id=1,
            top_k=3,
            document_ids=[],
        )

        with self._capture_stdout():
            result = retrieve(req)

        self.assertEqual(
            [d.document_id for d in result.documents],
            [d.document_id for d in expected],
        )
        self.assertEqual(
            [d.chunk_id for d in result.documents],
            [d.chunk_id for d in expected],
        )
        self.assertEqual(
            [d.score for d in result.documents],
            [d.score for d in expected],
        )

    def test_c_preview_does_not_exceed_limit(self):
        req = RetrieveRequest(
            query="문서 요약해줘",
            owner_user_id=1,
            top_k=3,
            document_ids=[],
        )

        with self._capture_stdout() as out:
            retrieve(req)

        log = out.getvalue()
        # semantic_raw/semantic_selected 로그 안의 각 preview 값이
        # 120자를 넘지 않아야 한다 - 원본 content(각 청크 약 200자
        # 이상)보다는 반드시 짧아야 한다.
        import ast
        import re as _re

        for match in _re.finditer(r"results=(\[.*?\])(?:\n|$)", log):
            summaries = ast.literal_eval(match.group(1))
            for item in summaries:
                if "preview" in item:
                    self.assertLessEqual(len(item["preview"]), 120)

    def test_d_logging_helper_does_not_mutate_document_objects(self):
        documents = [
            Document(
                document_id=1,
                chunk_id=101,
                chunk_index=0,
                title="문서A",
                document_type="OTHER",
                description=None,
                content="원본 content 그대로 유지되어야 함" * 10,
                score=0.9,
            )
        ]
        original_content = documents[0].content
        original_score = documents[0].score

        summaries = document_log_summary(documents, preview_limit=50)

        # 원본 Document는 절대 바뀌면 안 된다.
        self.assertEqual(documents[0].content, original_content)
        self.assertEqual(documents[0].score, original_score)
        # 반환된 summary는 원본과 별개의 새 dict(참조가 아님).
        self.assertIsInstance(summaries, list)
        self.assertIsInstance(summaries[0], dict)
        self.assertLessEqual(len(summaries[0]["preview"]), 50)

    def _capture_stdout(self):
        import io

        return contextlib.redirect_stdout(io.StringIO())


class SemanticErrorFallbackLogTest(unittest.TestCase):
    """목표 E: lexical fallback 조건에서 로그가 남는지만 확인한다.
    실제 lexical DB 검색(retrieve_scoped_lexical 내부)은 mock으로 대체한다."""

    def test_embedding_failure_logs_fallback_reason(self):
        with patch(
            "app.services.retrieval.rag_retriever.encode_query",
            side_effect=RuntimeError("embedding backend unavailable"),
        ), patch(
            "app.services.retrieval.rag_retriever.retrieve_scoped_lexical",
            return_value=RetrieveResponse(documents=[]),
        ) as mock_lexical:
            req = RetrieveRequest(
                query="이 문서 요약해줘",
                owner_user_id=1,
                top_k=3,
                document_ids=[42],
            )

            with contextlib.redirect_stdout(__import__("io").StringIO()) as out:
                retrieve(req)

            log = out.getvalue()
            self.assertIn(
                "[RAG] fallback='scoped_lexical' reason='semantic_error'",
                log,
            )
            mock_lexical.assert_called_once()

    def test_empty_after_retrieval_rule_logs_fallback_reason(self):
        # document_ids가 있으면 min_score가 -1.0으로 완화되므로(모든
        # score를 받아들임), "필터링돼서 비는" 상황이 아니라 애초에 pgvector
        # 후보 자체가 0건인 경우로 재현한다.
        empty_rows: list[tuple] = []

        with patch(
            "app.services.retrieval.rag_retriever.encode_query",
            return_value=__import__("numpy").zeros(4),
        ), patch(
            "app.services.retrieval.rag_retriever.get_connection",
            return_value=_fake_connection(empty_rows),
        ), patch(
            "app.services.retrieval.rag_retriever.retrieve_scoped_lexical",
            return_value=RetrieveResponse(documents=[]),
        ) as mock_lexical:
            req = RetrieveRequest(
                query="문서 요약해줘",
                owner_user_id=1,
                top_k=3,
                document_ids=[42],
            )

            with contextlib.redirect_stdout(__import__("io").StringIO()) as out:
                retrieve(req)

            log = out.getvalue()
            self.assertIn(
                "[RAG] fallback='scoped_lexical' "
                "reason='empty_after_retrieval_rule'",
                log,
            )
            mock_lexical.assert_called_once()


if __name__ == "__main__":
    unittest.main()