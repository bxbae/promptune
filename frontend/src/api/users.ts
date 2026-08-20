// UserController(/api/users) 전용 API 클라이언트.
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

// PUT /api/users/company - 회사 ID 수동 설정/수정 (MS 연동 시 자동으로도 채워짐)
export async function updateCompanyId(companyId: string): Promise<{ ok: boolean; companyId: string }> {
  const res = await fetch(`${API}/api/users/company`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ companyId }),
  });
  if (!res.ok) throw new Error(`회사 ID 저장 실패: ${res.status}`);
  return res.json();
}
