from __future__ import annotations

from app.schemas.models import Document


MAX_CONTENT_LENGTH = 1500
MAX_DESCRIPTION_LENGTH = 400


def build_internal_context(
    documents: list[Document],
) -> str:
    """
    BGE-M3 + pgvector Top-K 검색 결과를
    Generation 모델(HCX)에 전달할 내부문서 context로 변환한다.
    """

    if not documents:
        return "없음"

    parts: list[str] = []

    for index, doc in enumerate(documents, start=1):
        content = doc.content.strip()

        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]

        description = (doc.description or "").strip()

        if not description:
            description = "설명 없음"

        if len(description) > MAX_DESCRIPTION_LENGTH:
            description = description[:MAX_DESCRIPTION_LENGTH]

        parts.append(
            f"[내부 문서 {index}]\n"
            f"제목: {doc.title}\n"
            f"문서 유형: {doc.document_type}\n"
            f"설명: {description}\n"
            f"관련 내용:\n{content}"
        )

    return "\n\n".join(parts)
