"use client";
import { useRouter } from "next/navigation";

/**
 * mock 데이터 — 실제로는 백엔드에 "대화(세션) 목록 조회" API가 아직 없어서
 * 임시로 하드코딩함. 나중에 GET /api/chats 같은 엔드포인트가 생기면
 * 이 배열만 fetch 결과로 교체하면 됨.
 */
type ChatSummary = {
  id: string;
  title: string;      // 첫 프롬프트(요약)
  taskType: string;   // email / report / notice ...
  updatedAt: string;   // 상대시간 (ex. 3시간 전)
};

// TODO: 채팅은 목업 데이터, 배포 시 삭제 후 실제 DB와 연결
const MOCK_CHATS: ChatSummary[] = [
  { id: "1", title: "김대리에게 보고서 제출 요청 메일 정중하게 보내줘", taskType: "email", updatedAt: "3시간 전" },
  { id: "2", title: "팀 공지 초안 작성해줘", taskType: "notice", updatedAt: "어제" },
  { id: "3", title: "외부 협력사 견적 문의 메일 써줘", taskType: "email", updatedAt: "2일 전" },
  { id: "4", title: "주간 보고 요약 정리해줘", taskType: "report", updatedAt: "3일 전" },
  { id: "5", title: "신규 거래처 첫 인사 메일 작성", taskType: "email", updatedAt: "1주 전" },
];

const TASK_LABEL: Record<string, string> = {
  email: "이메일", report: "보고서", notice: "공지", application: "신청서", support: "문의",
};

export default function ChatsPage() {
  const router = useRouter();

  return (
    <div>
      <h1>채팅</h1>

      {/* TODO : 배포 시 MOCK이 아니라 실제 DB와 연결 */}
      {/* TODO : 채팅 리스트 페이징 처리 필요 */}
      {MOCK_CHATS.length === 0 ? (
        <div>아직 대화 기록이 없어요. <span style={{ color: "var(--accent)", fontWeight: 600}}>+ 새 채팅</span>으로 시작해보세요.</div>
      ) : (
        <div className="chat-list">
          {MOCK_CHATS.map((c) => (
            <button
              key={c.id}
              className="chat-list-item"
              onClick={() => router.push(`/chat?id=${c.id}`)}
            >
              <span className="chat-list-title">{c.title}</span>
              <span className="chat-list-meta">
                <span className="chat-list-badge">{TASK_LABEL[c.taskType] ?? c.taskType}</span>
                <span className="chat-list-time">{c.updatedAt}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}