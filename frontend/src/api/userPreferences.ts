// UserPreferenceController(/api/users/me/preferences) 전용 API 클라이언트.
// 이 엔드포인트들은 Authentication이 필요함
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface UserPreference {
  userId: number;
  speed: string;    // "fast" | "accurate"
  detail: string;   // "brief" | "detailed"
  preserve: string; // "keep" | "improve"
}

export interface UpsertPreferenceRequest {
  speed: string | null;
  detail: string | null;
  preserve: string | null;
}

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

// GET /api/users/me/preferences - 온보딩 완료 여부 판단 + 현재 설정값 조회
// 아직 미완료 시 백엔드가 404 내림 -> null 반환 (에러 X)
export async function getPreference(): Promise<UserPreference | null> {
  const res = await fetch(`${API}/api/users/me/preferences`, {
    headers: authHeaders(),
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`개인화 설정 조회 실패: ${res.status}`);
  return res.json();
}

// PUT /api/users/me/preferences - 온보딩 완료 시 최초 저장
// 이후엔 설정 변경 시 같은 API로 덮어씀
export async function upsertPreference(req: UpsertPreferenceRequest): Promise<UserPreference> {
  const res = await fetch(`${API}/api/users/me/preferences`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`개인화 설정 저장 실패: ${res.status}`);
  return res.json();
}