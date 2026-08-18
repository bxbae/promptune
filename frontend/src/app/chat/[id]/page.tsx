"use client";
import { useState, useRef, useEffect } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { execute } from "@/lib/api";
import { getChatMessages } from "@/api/chatSessions";
import PromptEditor from "@/components/PromptEditor";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const STATUS_STEPS = ["업무 유형 분석 중", "필요한 정보 확인 중", "답변 생성 중"];

export default function ChatThreadPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const chatSessionId = Number(params.id);
  const isFresh = searchParams.get("run") === "1";  // /chat(새 채팅)에서 막 넘어온 경우

  const [messages, setMessages] = useState<Message[]>([]);
  const [statusStep, setStatusStep] = useState<number | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(!isFresh);
  const [historyError, setHistoryError] = useState("");
  const threadEndRef = useRef<HTMLDivElement>(null);
  const ranRef = useRef(false);
  // isFresh : URL의 ?run=1 쿼리로 판단
  // 첫 메시지 전송 후 router.replace로 쿼리를 지우면 isFresh=false로 바뀌며 방금 보낸 메시지를 덮어써버리는 문제 발생
  // 페이지 진입시점에 fresh였는지를 1회성 값으로 고정해서 사용 >> isFreshRef
  const isFreshRef = useRef(isFresh);

  // randomUUID()는 https/로컬에서만 동작하는 secure context 전용이라
  // crypto.randomUUID() >> generateId()로 교체하여 사용
  const idCounter = useRef(0);
  function generateId() {
    return `msg-${Date.now()}-${idCounter.current++}`;
  }

  useEffect(() => {
    if (isFresh && !ranRef.current) {
      ranRef.current = true;
      const firstPrompt = sessionStorage.getItem(`chat-first-${chatSessionId}`);
      sessionStorage.removeItem(`chat-first-${chatSessionId}`);
      if (firstPrompt) {
        setMessages([{ id: generateId(), role: "user", content: firstPrompt }]);
        runAssistant(firstPrompt);
      }
      router.replace(`/chat/${chatSessionId}`);
    }
  }, [chatSessionId]);

  // 기존 대화(옛 채팅 클릭)로 들어온 경우, 지난 메시지 목록을 불러와서 대화형으로 표시
  useEffect(() => {
    if (isFreshRef.current) return; // 새 채팅 첫 메시지일 시 재조회하지 않음
    let cancelled = false;
    setLoadingHistory(true);
    setHistoryError("");

    getChatMessages(chatSessionId)
      .then((history) => {
        if (cancelled) return;
        const loaded: Message[] = history.flatMap((m) => {
          const pair: Message[] = [];
          if (m.prompt) pair.push({ id: `hist-${m.id}-user`, role: "user", content: m.prompt });
          if (m.aiResponse) pair.push({ id: `hist-${m.id}-assistant`, role: "assistant", content: m.aiResponse });
          return pair;
        });
        setMessages(loaded);
      })
      .catch((e) => {
        if (!cancelled) setHistoryError(e.message || "지난 메시지를 불러오지 못했습니다.");
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });

    return () => { cancelled = true; };
  }, [chatSessionId]);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, statusStep]);

  async function runAssistant(prompt: string) {
    setStatusStep(0);
    const stepTimer = setInterval(() => {
      setStatusStep((s) => (s === null ? null : Math.min(s + 1, STATUS_STEPS.length - 1)));
    }, 550);

    try {
      const res = await execute(prompt, chatSessionId);
      const resultText = res?.result?.result ?? JSON.stringify(res);
      clearInterval(stepTimer);
      setStatusStep(null);
      setMessages((prev) => [...prev, { id: generateId(), role: "assistant", content: resultText }]);

      // 새로 생성된 채팅 목록의 title을 불러옴
      window.dispatchEvent(
        new CustomEvent("chat-session-updated", {
          detail: {
            chatSessionId,
          },
        })
      );

    } catch {
      clearInterval(stepTimer);
      setStatusStep(null);
      setMessages((prev) => [
        ...prev,
        { id: generateId(), role: "assistant", content: "결과를 생성하지 못했습니다. 잠시 후 다시 시도해주세요." },
      ]);
    }
  }

  function handleSubmit(text: string) {
    if (statusStep !== null) return;
    setMessages((prev) => [...prev, { id: generateId(), role: "user", content: text }]);
    runAssistant(text);
  }

  const hasThread = messages.length > 0;

  return (
    <div className="chat-page has-thread">
      {!isFresh && loadingHistory && (
        <div className="no-thread-box">
          <span>지난 대화를 불러오는 중...</span>
        </div>
      )}

      {!isFresh && !loadingHistory && historyError && (
        <div className="no-thread-box">
          <span>{historyError}</span>
        </div>
      )}

      {!isFresh && !loadingHistory && !historyError && !hasThread && (
        <div className="no-thread-box">
          <span>
            아직 이 대화에 메시지가 없어요.<br />
            아래에 새로 작성하시면 같은 대화(#{chatSessionId})로 계속 저장됩니다.
          </span>
        </div>
      )}

      {hasThread && (
        <div className="thread">
          {messages.map((m) => (
            <div className={`msg-row ${m.role}`} key={m.id}>
              {m.role === "user" ? (
                <div className="msg-bubble user">{m.content}</div>
              ) : (
                <div className="msg-assistant">
                  <div className="msg-sender">PROMPTUNE</div>
                  <div className="msg-bubble assistant">{m.content}</div>
                </div>
              )}
            </div>
          ))}

          {statusStep !== null && (
            <div className="msg-assistant">
              <div className="msg-sender">PROMPTUNE</div>
              <div className="status-box">
                <div className="status-title">답변 생성 중 <span className="dots">···</span></div>
                {STATUS_STEPS.map((label, i) => (
                  <div key={label} className={`status-step ${i < statusStep ? "done" : i === statusStep ? "current" : ""}`}>
                    {i < statusStep ? "✓" : "•"} {label}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div ref={threadEndRef} />
        </div>
      )}

      <PromptEditor
        onSubmit={handleSubmit}
        disabled={statusStep != null || loadingHistory}
        compact
        placeholder="다음 프롬프트를 입력하세요"
      />
    </div>
  )
}