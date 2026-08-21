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
export async function analyze(
  text: string, signal: AbortSignal
): Promise<AnalyzeResponse> {
  const res = await fetch(`${API}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ text }),
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
