// ConsentController(/api/consents) 전용 API 클라이언트.
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

// POST /api/consents - consentType: "save" | "no_save". receiverProfileId 없으면 전체 동의.
export async function grantConsent(
  consentType: "save" | "no_save",
  receiverProfileId?: number
): Promise<void> {
  const res = await fetch(`${API}/api/consents`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ consentType, receiverProfileId: receiverProfileId ?? null }),
  });
  if (!res.ok) throw new Error(`동의 저장 실패: ${res.status}`);
}

// GET /api/consents/status - receiverProfileId 없으면 전체 기준으로 조회
// 2026-09-08: 토큰 만료(401)와 실제 미동의를 프론트가 구분할 수 있도록,
// 실패 시 백엔드가 보낸 X-Auth-Error 헤더를 에러 객체에 실어서 던진다.
export async function getConsentStatus(receiverProfileId?: number): Promise<boolean> {
  const url = new URL(`${API}/api/consents/status`);
  if (receiverProfileId != null) url.searchParams.set("receiverProfileId", String(receiverProfileId));

  const res = await fetch(url.toString(), { headers: authHeaders() });
  if (!res.ok) {
    const err = new Error(`동의 여부 조회 실패: ${res.status}`) as Error & { authError?: string };
    err.authError = res.headers.get("X-Auth-Error") ?? undefined;
    throw err;
  }
  const data = await res.json();
  return Boolean(data.allowed);
}
