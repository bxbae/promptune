// DocumentController(/api/documents) 전용 API 클라이언트.
// 현재 백엔드는 실제 파일 업로드가 아니라 title/tag/content를 JSON으로 받는 방식.
// 실제 파일 첨부/파싱은 아직 X

import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface DocumentItem {
  id: number;
  ownerUserId: number;
  title: string;
  tag: string; // "일반" | "업무"
  s3Key: string | null;
  fileType: string | null;
}

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

export interface UploadDocumentInput {
  title: string;
  tag: "일반" | "업무";
  content: string;
  fileType?: string;
}

// Create - POST /api/documents
export async function uploadDocument(input: UploadDocumentInput): Promise<DocumentItem> {
  const res = await fetch(`${API}/api/documents`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(input),
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

// Update - PATCH /api/documents/{id} - title, tag만 수정 가능
// TODO : 파일 자체 Update (덮어쓰기) 기능 추가 필요
export async function updateDocument(
  id: number,
  patch: { title?: string; tag?: "일반" | "업무" }
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