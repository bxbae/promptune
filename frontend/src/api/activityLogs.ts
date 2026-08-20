// ActivityLogController(/api/activity-logs) 전용 API 클라이언트.
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export type ActivityType = "applied" | "rejected" | "edited";

export interface ActivityLogEntry {
  type: ActivityType;
  label: string;
  chatSessionId: number | null;
  occurredAt: string;
}

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

// GET /api/activity-logs?filter=applied|rejected|edited (filter 생략 시 전체)
export async function listActivityLogs(filter?: ActivityType): Promise<ActivityLogEntry[]> {
  const url = new URL(`${API}/api/activity-logs`);
  if (filter) url.searchParams.set("filter", filter);

  const res = await fetch(url.toString(), { headers: authHeaders() });
  if (!res.ok) throw new Error(`활동 로그 조회 실패: ${res.status}`);
  return res.json();
}
