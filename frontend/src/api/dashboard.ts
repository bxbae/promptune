// DashboardController(/api/dashboard) 전용 API 클라이언트.
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface ElementCoverage {
  element: string;
  acceptCount: number;
  dismissCount: number;
  coverageRate: number; // 0~1
}

export interface ApplyRate {
  total: number;
  applied: number;
  applyRate: number; // 0~1
}

export interface ToneApplyRate {
  element: string;
  acceptCount: number;
  dismissCount: number;
  coverageRate: number; // 0~1
}

export interface SatisfactionRate {
  total: number;
  good: number;
  satisfactionRate: number; // 0~1
}

// task_type 문자열 -> 건수
export type TaskTypeDistribution = Record<string, number>;

// 날짜문자열(YYYY-MM-DD) -> 그날 프롬프트 세션 개수. 데이터 없는 날짜는 아예 키가 없음.
export type WeeklyActivity = Record<string, number>;

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`대시보드 데이터 조회 실패: ${res.status}`);
  return res.json();
}

export const getElementCoverage = () => get<ElementCoverage[]>("/api/dashboard/element-coverage");
export const getApplyRate = () => get<ApplyRate>("/api/dashboard/apply-rate");
export const getWeeklyActivity = () => get<WeeklyActivity>("/api/dashboard/weekly-activity");
export const getToneApplyRate = () => get<ToneApplyRate>("/api/dashboard/tone-apply-rate");
export const getSatisfactionRate = () => get<SatisfactionRate>("/api/dashboard/satisfaction-rate");
export const getTaskTypeDistribution = () => get<TaskTypeDistribution>("/api/dashboard/task-type-distribution");