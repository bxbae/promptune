"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listChatSessions, ChatSession } from "@/api/chatSessions";

function timeAgo(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return "방금 전";
  if (min < 60) return `${min}분 전`;
  const hour = Math.floor(min / 60);
  if (hour < 24) return `${hour}시간 전`;
  const day = Math.floor(hour / 24);
  if (day === 1) return "어제";
  if (day < 7) return `${day}일 전`;
  return `${Math.floor(day / 7)}주 전`;
}

const TASK_LABEL: Record<string, string> = {
  email: "이메일", report: "보고서", notice: "공지", application: "신청서", support: "문의",
};

const PAGE_SIZE = 10;

export default function ChatsPage() {
  const router = useRouter();
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    listChatSessions()
      .then(setChats)
      .catch((e) => setError(e.message || "채팅 목록을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  // AppShell(사이드바)에서 채팅 삭제 시, 이 페이지가 열려있으면 목록에서 실시간으로 제거
  useEffect(() => {
    function handleDeleted(e: Event) {
      const { chatSessionId } = (e as CustomEvent).detail || {};
      if (chatSessionId == null) return;
      setChats((prev) => prev.filter((c) => c.id !== chatSessionId));
    }
    
    window.addEventListener("chat-session-deleted", handleDeleted);
    return () => window.removeEventListener("chat-session-deleted", handleDeleted);
  }, []);

  // 삭제로 인해 현재 페이지에 항목이 없어지면 이전 페이지로 자동 이동
  useEffect(() => {
    const maxPage = Math.max(1, Math.ceil(chats.length / PAGE_SIZE));
    if (page > maxPage) setPage(maxPage);
  }, [chats, page]);

  return (
    <div>
      <h1>채팅</h1>

      {loading && <div style={{ color: "var(--muted)" }}>불러오는 중...</div>}
      {!loading && error && <div style={{ color: "var(--block)" }}>{error}</div>}

      {!loading && !error && chats.length === 0 && (
        <div style={{ padding: "60px 0", textAlign: "center", color: "var(--muted)" }}>
          아직 대화 기록이 없어요. <span style={{ color: "var(--accent)", fontWeight: 600 }}>+ 새 채팅</span>으로 시작해보세요.
        </div>
      )}

      {!loading && !error && chats.length > 0 && (
        <>
          <div className="chat-list">
            {chats.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((c) => (
              <button
                key={c.id}
                className="chat-list-item"
                onClick={() => router.push(`/chat/${c.id}`)}
              >
                <span className="chat-list-title">{c.title || `대화 #${c.id}`}</span>
                <span className="chat-list-meta">
                  {/* {c.taskType && (
                    <span className="chat-list-badge">{TASK_LABEL[c.taskType] ?? c.taskType}</span>
                  )} */}
                  <span className="chat-list-time">{timeAgo(c.updatedAt)}</span>
                </span>
              </button>
            ))}
          </div>

          {chats.length > PAGE_SIZE && (
            <div className="chat-list-pager">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                이전
              </button>
              <span className="chat-list-pager-status">
                {page} / {Math.ceil(chats.length / PAGE_SIZE)}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(Math.ceil(chats.length / PAGE_SIZE), p + 1))}
                disabled={page === Math.ceil(chats.length / PAGE_SIZE)}
              >
                다음
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}