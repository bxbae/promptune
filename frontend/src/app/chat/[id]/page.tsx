"use client";
import { useState, useRef, useEffect } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { execute } from "@/lib/api";
import { generateId } from "@/lib/id";
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
  const threadEndRef = useRef<HTMLDivElement>(null);
  const ranRef = useRef(false);

  // randomUUID()는 https/로컬에서만 동작하는 secure context 전용이라
  // crypto.randomUUID() >> nextId()로 교체하여 사용
  const idCounter = useRef(0);
  function nextId() {
    return `msg-${Date.now()}-${idCounter.current++}`;
  }

  useEffect(() => {
    if (isFresh && !ranRef.current) {
      ranRef.current = true;
      const firstPrompt = sessionStorage.getItem(`chat-first-${chatSessionId}`);
      sessionStorage.removeItem(`chat-first-${chatSessionId}`);
      if (firstPrompt) {
        setMessages([{ id: nextId(), role: "user", content: firstPrompt }]);
        runAssistant(firstPrompt);
      }
      router.replace(`/chat/${chatSessionId}`);
    }
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
      setMessages((prev) => [...prev, { id: nextId(), role: "assistant", content: resultText }]);

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
        { id: nextId(), role: "assistant", content: "결과를 생성하지 못했습니다. 잠시 후 다시 시도해주세요." },
      ]);
    }
  }

  function handleSubmit(text: string) {
    if (statusStep !== null) return;
    setMessages((prev) => [...prev, { id: nextId(), role: "user", content: text }]);
    runAssistant(text);
  }

  const hasThread = messages.length > 0;

  return (
    <div className="chat-page has-thread">
      {!isFresh && !hasThread && (
        <div className="no-thread-box">
          <span>
            이 대화의 지난 메시지를 불러오는 기능은 아직 없어요.<br />
            아래에 새로 이어서 작성하시면 같은 대화(#{chatSessionId})로 계속 저장됩니다.
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
        disabled={statusStep != null}
        compact
        placeholder="다음 프롬프트를 입력하세요"
      />
    </div>
  )
}