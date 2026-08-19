// PromptSessionController(/api/prompt-sessions) 전용 API 클라이언트.
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

// POST /api/prompt-sessions/{id}/edits
// 만족도(👍/👎) 저장과 "직접수정"(원본/최종본) 저장을 겸용
// satisfaction만 보낼 땐 generatedResult/userFinalResult는 생략 가능
export async function submitPromptSessionEdit(
  promptSessionId: number,
  payload: { satisfaction?: "good" | "bad"; generatedResult?: string; userFinalResult?: string }
): Promise<void> {
  const res = await fetch(`${API}/api/prompt-sessions/${promptSessionId}/edits`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`저장 실패: ${res.status}`);
}
