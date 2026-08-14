// ChatSesionController(/api/chat-sessions) 전용 API 클라이언트.
// 이 엔드포인트들은 Authentication이 필요함
// >> analyze/execute(lib/api.ts, permitAll)와 달리 토큰을 반드시 헤더에 실어보냄.
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface ChatSession {
  id: number;
  userId: number;
  title: string | null;
  updatedAt: string;
}

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

// POST /api/chat-sessions - "+ 새 채팅" 시 빈 대화 세션 생성
export async function createChatSession(): Promise<ChatSession> {
  const res = await fetch(`${API}/api/chat-sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  if (!res.ok) throw new Error(`대화 생성 실패: ${res.status}`);
  return res.json();
}

// GET /api/chat-sessions - 로그인한 사용자의 대화 목록 (최신순)
export async function listChatSessions(): Promise<ChatSession[]> {
  const res = await fetch(`${API}/api/chat-sessions`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`대화 목록 조회 실패: ${res.status}`);
  return res.json();
}

// TODO (백엔드 확인/구현 필요)
// GET /api/chat-sessions/{id}/messages 같은 "세션 하나의 메세지 목록 조회" 엔드포인트