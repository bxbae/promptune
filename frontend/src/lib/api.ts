// 백엔드 API 호출. 흐름도 2번(입력중단 감지·이전요청 취소)의 AbortController 포함.
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface DiagnoseResult {
  missing: Record<string, number>;
  taskType: string;
  typos: { span: string; suggest: string }[];
  needsInternalDocs: boolean;
}
export interface AnalyzeResponse {
  gate: { passed: boolean; reason: string };
  diagnose: DiagnoseResult | null;
  recommend: { targetElements: string[] } | null;
}

// 2번: 분석 요청 (이전 요청은 signal로 취소)
// TODO: execute()와 같은 userId 하드코딩문제 있음
// /api/analyze도 인증 필요로 바꾸고 Authentication에서 유저를 뽑도록 고치면
// 여기서도 userId 제거 + authHeaders() 추가.
export async function analyze(
  text: string, signal: AbortSignal
): Promise<AnalyzeResponse> {
  const res = await fetch(`${API}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, userId: 1 }),
    signal,
  });
  if (!res.ok) throw new Error(`분석 실패: ${res.status}`);
  return res.json();
}

// 11번: 실행
export async function execute(finalPrompt: string, chatSessionId?: number) {
  const res = await fetch(`${API}/api/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ finalPrompt, chatSessionId }),
  });
  if (!res.ok) throw new Error(`실행 실패: ${res.status}`);
  return res.json();
}
