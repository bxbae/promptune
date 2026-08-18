// PersonalizationController(/api/users/me/personalization) + 채팅 이력 전체 삭제 전용 API 클라이언트.
// 히스토리 > 개인화 설정 화면의 "전체 초기화"/"내보내기"/"작업 이력 전체 삭제" 버튼에서 사용.
import { getToken } from "@/lib/auth";
import { UserPreference } from "@/api/userPreferences";

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

export interface PersonalizationExport {
  preferences: UserPreference | null;
  receivers: ReceiverProfile[];
  globalConsentGranted: boolean;
}

function authHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("로그인이 필요합니다.");
  return { Authorization: `Bearer ${token}` };
}

// DELETE /api/users/me/personalization - 습관 데이터(선호 설정) + 수신자 프로필 + 관련 동의/학습 데이터 전체 삭제
export async function resetPersonalization(): Promise<void> {
  const res = await fetch(`${API}/api/users/me/personalization`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`개인화 데이터 초기화 실패: ${res.status}`);
}

// GET /api/users/me/personalization/export - 선호 설정 + 수신자 프로필 + 동의 여부 내보내기
export async function exportPersonalization(): Promise<PersonalizationExport> {
  const res = await fetch(`${API}/api/users/me/personalization/export`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`개인화 데이터 내보내기 실패: ${res.status}`);
  return res.json();
}

// DELETE /api/chat-sessions - 작업 이력(채팅/프롬프트 기록) 전체 삭제
export async function deleteAllChatHistory(): Promise<void> {
  const res = await fetch(`${API}/api/chat-sessions`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`작업 이력 삭제 실패: ${res.status}`);
}
