// DocumentController(/api/documents) 전용 API 클라이언트.
// 실제 파일을 multipart/form-data로 업로드하면 백엔드가 S3(promptune-document 버킷)에 저장하고
// 메타데이터(title/documentType/s3Key/fileType)를 DB에 저장한다.

import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface DocumentItem {
  id: number;
  ownerUserId: number;
  title: string;
  documentType: string; // "규정" | "양식" | "가이드" | "보고서" | "기타"
  s3Key: string | null;
  fileType: string | null;
}

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

// Create - POST /api/documents (multipart/form-data)
// 주의: FormData를 쓸 때는 Content-Type 헤더를 직접 지정하면 안 됨
// (브라우저가 boundary를 포함해서 자동으로 설정해야 함)
export async function uploadDocument(
  file: File,
  title: string,
  documentType: "규정" | "양식" | "가이드" | "보고서" | "기타"
): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", title);
  formData.append("documentType", documentType);

  const res = await fetch(`${API}/api/documents`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  if (!res.ok) throw new Error(`업로드 실패: ${res.status}`);
  return res.json();
}

// Read - GET /api/documents
export async function listDocuments(): Promise<DocumentItem[]> {
  const res = await fetch(`${API}/api/documents`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`파일 목록 조회 실패: ${res.status}`);
  return res.json();
}

// Update - PATCH /api/documents/{id} - title, documentType만 수정 가능
// TODO : 파일 자체 Update (덮어쓰기) 기능 추가 필요
export async function updateDocument(
  id: number,
  patch: { title?: string; documentType?: "규정" | "양식" | "가이드" | "보고서" | "기타" }
): Promise<DocumentItem> {
  const res = await fetch(`${API}/api/documents/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`수정 실패: ${res.status}`);
  return res.json();
}

// Delete - DELETE /api/documents/{id}
export async function deleteDocument(id: number): Promise<void> {
  const res = await fetch(`${API}/api/documents/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`삭제 실패: ${res.status}`);
}