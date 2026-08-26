import sys
import types
import unittest
from unittest.mock import patch

# 2026-08-26: retrieval_orchestrator -> conversation_context가 모듈 최상단에서
# `import torch`를 하는데(실제 HCX 추론은 지연 로딩이라 무거운 모델 자체는
# 여기서 안 올라옴), 이 테스트 샌드박스에는 torch가 설치돼 있지 않다
# (ai-service Docker 이미지에서는 transformers/FlagEmbedding의 전이
# 의존성으로 항상 설치되어 있음 - requirements.txt 참고). import 자체만
# 통과시키면 되므로 최소한의 더미 모듈로 대체한다.
if "torch" not in sys.modules:
    import contextlib

    _torch_stub = types.ModuleType("torch")
    _torch_stub.inference_mode = contextlib.nullcontext

    class _StubTensor:  # scipy/sklearn의 array-api 호환 체크가 torch.Tensor를
        pass            # getattr/issubclass로 조회하길래 최소한만 채워둠.

    _torch_stub.Tensor = _StubTensor
    sys.modules["torch"] = _torch_stub

# conversation_context가 실제로 필요로 하는 건 hcx_lock/load_hcx_runtime
# "함수가 존재한다"는 것뿐 - 이 테스트는 두 함수 다 호출되지 않는 경로만
# 다루므로(document_ids가 있거나, 대화 이력 자체가 없거나 짧은 케이스),
# transformers(및 그게 필요로 하는 실제 torch 런타임) 전체를 로드할 필요가
# 없다. hcx_runtime 모듈 자체를 더미로 대체해서 무거운 import 체인을 끊는다.
if "app.services.hcx_runtime" not in sys.modules:
    import contextlib

    _hcx_runtime_stub = types.ModuleType("app.services.hcx_runtime")

    def _unexpected_hcx_call(*args, **kwargs):
        raise AssertionError(
            "이 테스트 경로에서는 HCX 런타임이 호출되면 안 됨"
        )

    _hcx_runtime_stub.hcx_lock = lambda timeout=None: contextlib.nullcontext()
    _hcx_runtime_stub.load_hcx_runtime = _unexpected_hcx_call
    sys.modules["app.services.hcx_runtime"] = _hcx_runtime_stub

from app.schemas.models import ConversationMessage, RetrievalExecuteRequest, RetrieveResponse, Document
from app.services.retrieval.retrieval_orchestrator import execute_retrieval


class DocumentIdsRoutingTest(unittest.TestCase):
    """
    2026-08-26: DOCX를 첨부하고 "이게 무슨 내용인지 알려줘" 처럼 질문
    자체에는 "문서"/"파일" 같은 키워드가 전혀 없는 메시지를 보내면, ML
    라우터가 no_retrieval로 잘못 분류해서 첨부 문서 내용이 답변에 전혀
    반영되지 않고, 대신 이전 대화 주제가 그대로 튀어나오는 문제가 있었음.

    document_ids가 있으면 질의 텍스트/대화 맥락 override와 무관하게 항상
    internal_rag로 보내지고, 그 문서 id들이 실제 RetrieveRequest까지
    전달되는지 고정한다.
    """

    def test_document_ids_forces_internal_rag_even_without_doc_keywords(self):
        req = RetrievalExecuteRequest(
            query="이게 무슨 내용인지 알려줘",
            owner_user_id=1,
            top_k=3,
            history=[],
            document_ids=[42],
        )

        captured = {}

        def fake_retrieve(retrieve_req):
            captured["req"] = retrieve_req
            return RetrieveResponse(
                documents=[
                    Document(
                        document_id=42,
                        chunk_id=1,
                        chunk_index=0,
                        title="차승연_프로젝트_이력서_초안.docx",
                        document_type="OTHER",
                        description=None,
                        content="실제 문서 본문...",
                        score=1.0,
                    )
                ]
            )

        with patch(
            "app.services.retrieval.retrieval_orchestrator.pipeline_mock.retrieve",
            side_effect=fake_retrieve,
        ):
            result = execute_retrieval(req)

        self.assertEqual(result.route, "internal_rag")
        self.assertTrue(result.used_internal_rag)
        self.assertEqual(len(result.documents), 1)
        self.assertEqual(result.documents[0].document_id, 42)

        # RetrieveRequest에도 document_ids가 실제로 실려갔는지 확인
        self.assertEqual(captured["req"].document_ids, [42])

    def test_document_ids_overrides_conversation_route_override(self):
        # 대화 맥락상으로는 "그거 다시 알려줘" 같은 followup이 no_retrieval로
        # override 될 수 있는 상황이더라도, document_ids가 있으면 그보다
        # 우선해서 internal_rag로 가야 한다.
        req = RetrievalExecuteRequest(
            query="그거 다시 설명해줘",
            owner_user_id=1,
            top_k=3,
            history=[
                ConversationMessage(role="user", content="침착맨 몇살이야?"),
                ConversationMessage(role="assistant", content="확인이 어렵습니다."),
            ],
            document_ids=[7],
        )

        with patch(
            "app.services.retrieval.retrieval_orchestrator.pipeline_mock.retrieve",
            return_value=RetrieveResponse(documents=[]),
        ):
            result = execute_retrieval(req)

        self.assertEqual(result.route, "internal_rag")

    def test_no_document_ids_falls_back_to_existing_routing(self):
        # document_ids가 없을 때는 기존 동작(ML 라우팅)이 그대로 유지되어야
        # 한다 - 이번 수정이 회귀를 만들지 않았는지 확인.
        req = RetrievalExecuteRequest(
            query="오늘 날씨 어때?",
            owner_user_id=1,
            top_k=3,
            history=[],
            document_ids=[],
        )

        with patch(
            "app.services.retrieval.retrieval_orchestrator.search_web",
            return_value=[],
        ):
            result = execute_retrieval(req)

        self.assertIn(result.route, {"web_search", "external_or_realtime"})


if __name__ == "__main__":
    unittest.main()
