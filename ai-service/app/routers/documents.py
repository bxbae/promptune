from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.services.document_generator import generate_document


router = APIRouter(tags=["document-generator"])


class DocumentGenerateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    content: str = Field(..., min_length=1)
    format: Literal["pdf", "docx", "txt", "md"] = "pdf"


@router.post("/documents/generate")
def create_document(req: DocumentGenerateRequest):
    try:
        data, filename, media_type = generate_document(
            title=req.title,
            content=req.content,
            output_format=req.format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    encoded_filename = quote(filename)

    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition":
                f"attachment; filename*=UTF-8''{encoded_filename}"
        },
    )
