// ReceiverProfileController(/api/receiver-profiles) 전용 API 클라이언트.
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface ReceiverProfile {
  id: number;
  userId: number;
  receiverName: string;
  relationship: string | null;
  preferredTone: string | null;
  avgLength: number;
  applyRate: number | null;
  updatedAt: string;
}

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

// GET /api/receiver-profiles - 내 수신자 목록
export async function listReceiverProfiles(): Promise<ReceiverProfile[]> {
  const res = await fetch(`${API}/api/receiver-profiles`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`수신자 목록 조회 실패: ${res.status}`);
  return res.json();
}

// POST /api/receiver-profiles - 등록/갱신 (같은 이름이면 백엔드가 알아서 평균 계산하여 갱신)
export async function upsertReceiverProfile(
  receiverName: string,
  tone: string | null,
  length: number
): Promise<ReceiverProfile> {
  const res = await fetch(`${API}/api/receiver-profiles`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ receiverName, tone, length }),
  });
  if (!res.ok) throw new Error(`수신자 프로필 저장 실패: ${res.status}`);
  return res.json();
}

// PATCH /api/receiver-profiles/{id} - 관계·선호 톤·이름 수정
export async function updateReceiverProfile(
  id: number,
  patch: { relationship?: string | null; preferredTone?: string | null; receiverName?: string }
): Promise<ReceiverProfile> {
  const res = await fetch(`${API}/api/receiver-profiles/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`수정 실패: ${res.status}`);
  return res.json();
}

// DELETE /api/receiver-profiles/{id} - 학습된 프로필 초기화
export async function deleteReceiverProfile(id: number): Promise<void> {
  const res = await fetch(`${API}/api/receiver-profiles/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`삭제 실패: ${res.status}`);
}
