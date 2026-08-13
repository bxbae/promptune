from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np


EXPECTED_DIM = 1024


def load_list(path: Path, wrapper_key: str) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and wrapper_key in data:
        data = data[wrapper_key]

    if not isinstance(data, list):
        raise ValueError(
            f"{path}는 list 또는 {wrapper_key} list를 포함해야 합니다."
        )

    return data


def sql_text(value: str | None) -> str:
    if value is None:
        return "NULL"

    return "'" + str(value).replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--documents",
        default="ai-service/app/data/rag/rag_test_documents.json",
    )

    parser.add_argument(
        "--chunks",
        default="ai-service/app/data/rag/rag_test_chunks.json",
    )

    parser.add_argument(
        "--embeddings",
        default="ai-service/app/data/rag/rag_test_embeddings.npy",
    )

    parser.add_argument(
        "--owner-user-id",
        type=int,
        default=2,
    )

    args = parser.parse_args()

    documents = load_list(
        Path(args.documents),
        "documents",
    )

    chunks = load_list(
        Path(args.chunks),
        "chunks",
    )

    embeddings = np.load(args.embeddings)

    print("[1/4] 입력 데이터 확인")
    print(f"documents={len(documents)}")
    print(f"chunks={len(chunks)}")
    print(f"embeddings={embeddings.shape}")
    print(f"owner_user_id={args}")

    if len(documents) != 18:
        raise RuntimeError(
            f"테스트 문서는 18개여야 합니다: {len(documents)}"
        )

    if len(chunks) != embeddings.shape[0]:
        raise RuntimeError(
            "chunk 수와 embedding 수가 다릅니다: "
            f"{len(chunks)} != {embeddings.shape[0]}"
        )

    if embeddings.ndim != 2:
        raise RuntimeError(
            f"embedding이 2차원이 아닙니다: {embeddings.shape}"
        )

    if embeddings.shape[1] != EXPECTED_DIM:
        raise RuntimeError(
            f"embedding 차원이 {EXPECTED_DIM}이 아닙니다: "
            f"{embeddings.shape}"
        )

    document_ids = {}

    for document in documents:
        source_id = (
            document.get("id")
            or document.get("document_id")
        )

        if not source_id:
            raise ValueError(
                f"문서 ID가 없습니다: {document}"
            )

        document_ids[str(source_id)] = document

    print("[2/4] DB INSERT SQL 생성")

    sql_lines = [
        "BEGIN;",
        "",
        "DELETE FROM documents "
        f"WHERE owner_user_id = {args.owner_user_id} "
        "AND tag = 'BGE_M3_TEST';",
        "",
        "CREATE TEMP TABLE rag_doc_map (",
        "    source_document_id TEXT PRIMARY KEY,",
        "    db_document_id BIGINT NOT NULL",
        ");",
        "",
    ]

    for source_id, document in document_ids.items():
        title = document.get("title") or source_id

        sql_lines.extend([
            "WITH inserted AS (",
            "    INSERT INTO documents "
            "(owner_user_id, title, tag, s3_key, file_type)",
            "    VALUES ("
            f"{args.owner_user_id}, "
            f"{sql_text(title)}, "
            "'BGE_M3_TEST', "
            "NULL, "
            "'json'"
            ")",
            "    RETURNING id",
            ")",
            "INSERT INTO rag_doc_map "
            "(source_document_id, db_document_id)",
            f"SELECT {sql_text(source_id)}, id FROM inserted;",
            "",
        ])

    for index, chunk in enumerate(chunks):
        source_document_id = str(
            chunk.get("document_id")
        )

        chunk_index = int(
            chunk.get("chunk_index", index)
        )

        content = chunk.get("content")

        if source_document_id not in document_ids:
            raise RuntimeError(
                "원본 문서를 찾을 수 없습니다: "
                f"{source_document_id}"
            )

        if content is None:
            raise RuntimeError(
                f"chunk content가 없습니다: index={index}"
            )
        vector = embeddings[index]

        vector_sql = (
            "["
            + ",".join(
                format(float(value), ".9g")
                for value in vector
            )
            + "]"
        )

        sql_lines.extend([
            "INSERT INTO document_chunks "
            "(document_id, chunk_index, content, embedding)",
            "SELECT",
            "    db_document_id,",
            f"    {chunk_index},",
            f"    {sql_text(content)},",
            f"    {sql_text(vector_sql)}::vector",
            "FROM rag_doc_map",
            "WHERE source_document_id = "
            f"{sql_text(source_document_id)};",
            "",
        ])

    sql_lines.extend([
        "COMMIT;",
        "",
        "SELECT COUNT(*) AS test_documents",
        "FROM documents",
        f"WHERE owner_user_id = {args.owner_user_id}",
        "AND tag = 'BGE_M3_TEST';",
        "",
        "SELECT COUNT(*) AS test_chunks",
        "FROM document_chunks dc",
        "JOIN documents d ON d.id = dc.document_id",
        f"WHERE d.owner_user_id = {args.owner_user_id}",
        "AND d.tag = 'BGE_M3_TEST';",
        "",
        "SELECT COUNT(*) AS embedding_null_count",
        "FROM document_chunks dc",
        "JOIN documents d ON d.id = dc.document_id",
        f"WHERE d.owner_user_id = {args.owner_user_id}",
        "AND d.tag = 'BGE_M3_TEST'",
        "AND dc.embedding IS NULL;",
    ])

    sql = "\n".join(sql_lines)

    print("[3/4] PostgreSQL 저장")

    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "sh",
        "-lc",
        'psql -v ON_ERROR_STOP=1 '
        '-U "$POSTGRES_USER" '
        '-d "$POSTGRES_DB"',
    ]

    subprocess.run(
        command,
        input=sql,
        text=True,
        check=True,
    )

    print("[4/4] 완료")
    print("RAG TEST DATA DB IMPORT OK")


if __name__ == "__main__":
    main()
