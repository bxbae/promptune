from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+")


def normalize_text(text: str) -> str:
    """공백/줄바꿈을 정리하되 문장 내용은 유지한다."""
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    """
    한국어 문장을 마침표/물음표/느낌표/줄바꿈 기준으로 우선 분리한다.
    문장부호가 부족한 문서도 빈 문자열 없이 처리한다.
    """
    text = normalize_text(text)
    if not text:
        return []

    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return sentences if sentences else [text]


def split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    """
    문장 하나가 max_chars를 초과할 때만 강제 분할한다.
    가능하면 공백 위치에서 끊는다.
    """
    parts: list[str] = []
    remaining = sentence.strip()

    while len(remaining) > max_chars:
        cut = remaining.rfind(" ", 0, max_chars + 1)
        if cut < int(max_chars * 0.6):
            cut = max_chars

        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()

    if remaining:
        parts.append(remaining)

    return parts


def chunk_text(
    text: str,
    min_chars: int = 300,
    target_chars: int = 400,
    max_chars: int = 500,
) -> list[str]:
    """
    문장 경계를 최대한 보존하면서 약 300~500자 단위로 텍스트를 나눈다.

    원칙
    - 목표 크기: target_chars
    - 최대 크기: max_chars
    - 문장 중간 절단은 가능한 피함
    - 한 문장이 max_chars보다 긴 경우에만 강제 분할
    - 너무 짧은 마지막 chunk는 가능하면 앞 chunk와 합침
    """
    if not (0 < min_chars <= target_chars <= max_chars):
        raise ValueError("min_chars <= target_chars <= max_chars 조건이 필요합니다.")

    sentences: list[str] = []
    for sentence in split_sentences(text):
        if len(sentence) > max_chars:
            sentences.extend(split_long_sentence(sentence, max_chars))
        else:
            sentences.append(sentence)

    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        extra = len(sentence) + (1 if current else 0)

        # 현재 chunk에 문장을 더했을 때 최대 크기를 넘으면 먼저 확정
        if current and current_len + extra > max_chars:
            chunks.append(" ".join(current).strip())
            current = [sentence]
            current_len = len(sentence)
            continue

        current.append(sentence)
        current_len += extra

        # 목표 크기를 넘겼으면 자연스럽게 확정
        if current_len >= target_chars:
            chunks.append(" ".join(current).strip())
            current = []
            current_len = 0

    if current:
        tail = " ".join(current).strip()

        # 마지막 chunk가 너무 짧고 앞 chunk와 합쳐도 max_chars 이하라면 병합
        if (
            chunks
            and len(tail) < min_chars
            and len(chunks[-1]) + 1 + len(tail) <= max_chars
        ):
            chunks[-1] = f"{chunks[-1]} {tail}".strip()
        else:
            chunks.append(tail)

    return chunks


def chunk_documents(
    documents: Iterable[dict],
    min_chars: int = 300,
    target_chars: int = 400,
    max_chars: int = 500,
) -> list[dict]:
    """
    rag_test_documents.json 형식의 문서 목록을 chunk 목록으로 변환한다.
    """
    output: list[dict] = []

    for doc in documents:
        document_id = doc["id"]
        title = doc["title"]
        company_id = doc.get("company_id")
        content = doc["content"]

        chunks = chunk_text(
            content,
            min_chars=min_chars,
            target_chars=target_chars,
            max_chars=max_chars,
        )

        for chunk_index, chunk in enumerate(chunks):
            output.append(
                {
                    "chunk_id": f"{document_id}_CH{chunk_index:03d}",
                    "document_id": document_id,
                    "company_id": company_id,
                    "title": title,
                    "chunk_index": chunk_index,
                    "content": chunk,
                    "char_count": len(chunk),
                }
            )

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="PrompTune RAG test document chunker")
    parser.add_argument("--input", required=True, help="입력 documents JSON 경로")
    parser.add_argument("--output", required=True, help="출력 chunks JSON 경로")
    parser.add_argument("--min-chars", type=int, default=300)
    parser.add_argument("--target-chars", type=int, default=400)
    parser.add_argument("--max-chars", type=int, default=500)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open("r", encoding="utf-8") as f:
        documents = json.load(f)

    chunks = chunk_documents(
        documents,
        min_chars=args.min_chars,
        target_chars=args.target_chars,
        max_chars=args.max_chars,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"documents: {len(documents)}")
    print(f"chunks: {len(chunks)}")
    print(f"output: {output_path}")


if __name__ == "__main__":
    main()
