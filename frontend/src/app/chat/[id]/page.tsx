"use client";
import { useState, useRef, useEffect } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { execute } from "@/lib/api";
import { getChatMessages } from "@/api/chatSessions";
import { listReceiverProfiles, upsertReceiverProfile, ReceiverProfile } from "@/api/receiverProfiles";
import { grantConsent, getConsentStatus } from "@/api/consents";
import { submitPromptSessionEdit } from "@/api/promptSessions";
import PromptEditor from "@/components/PromptEditor";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  promptSessionId?: number;
}

// TODO: 정식 파이프라인 붙으면 수정
// 프롬프트를 통해 수신자 감지하는 단순한 휴리스틱
// 실제 개체명 인식X >> **님, **씨 패턴만 잡아내는 정규식
// 정식 8요소 분석 파이프라인이 붙기 전까지의 임시 로직
function detectReceiverName(prompt: string): string | null {
  const match = prompt.match(/([가-힣]{2,4})(님|씨)/);
  return match ? match[1] : null;
}

// TODO: 목업 - 나중에 백엔드/ai-service 실제 스타일 분석 붙으면 이 배열 자체를 없애고
// 백엔드가 내려주는 진짜 분석 결과로 교체할 것. 지금은 수신자와 무관하게 항상 같은 문구.
const MOCK_STYLE_HINTS = [
  "정중하지만 간결한 사내 업무체",
  "요청사항을 첫 문단에 배치",
  "마감일과 회신 요청을 자주 포함",
];

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

  // 저장된 개인화 데이터가 없는 수신자가 감지됐을 때 뜨는 동의 카드 (한 번에 1개)
  const [receiverProfiles, setReceiverProfiles] = useState<ReceiverProfile[]>([]);
  const [pendingConsent, setPendingConsent] = useState<
    { name: string; forMessageId: string; saving: boolean; done: boolean } | null
  >(null);

  useEffect(() => {
    listReceiverProfiles()
      .then(setReceiverProfiles)
      .catch(() => {}); // 실패해도 채팅 자체는 그대로 진행 (동의 카드만 안 뜸)
  }, []);

  // 만족도(👍/👎) - 메시지 id별로 선택 상태 기록 (한 번 누르면 고정, 재선택 불가 - 스토리보드 기준)
  const [satisfaction, setSatisfaction] = useState<Record<string, "good" | "bad">>({});

  async function rateSatisfaction(m: Message, value: "good" | "bad") {
    if (!m.promptSessionId || satisfaction[m.id]) return;
    setSatisfaction((prev) => ({ ...prev, [m.id]: value })); // 낙관적 업데이트
    try {
      await submitPromptSessionEdit(m.promptSessionId, { satisfaction: value });
    } catch {
      setSatisfaction((prev) => {
        const next = { ...prev };
        delete next[m.id];
        return next;
      });
      alert("저장에 실패했습니다.");
    }
  }

  async function applyConsent() {
    if (!pendingConsent) return;
    setPendingConsent((c) => (c ? { ...c, saving: true } : c));
    try {
      const lastAssistant = messages.find((m) => m.id === pendingConsent.forMessageId);
      // 1) 수신자 프로필 등록/갱신 (없으면 새로 생김, 있으면 톤·길이 평균 갱신)
      const saved = await upsertReceiverProfile(
        pendingConsent.name,
        null, // 톤 자동 감지 로직은 아직 없음 - null이면 이후 수동 수정 가능
        lastAssistant?.content.length ?? 0
      );
      // 2) 그 프로필 기준으로 저장 동의 기록
      await grantConsent("save", saved.id);

      setReceiverProfiles((prev) => {
        const exists = prev.some((p) => p.id === saved.id);
        return exists ? prev.map((p) => (p.id === saved.id ? saved : p)) : [...prev, saved];
      });
      setPendingConsent((c) => (c ? { ...c, saving: false, done: true } : c));
      setTimeout(() => setPendingConsent(null), 1500); // "저장했어요" 잠깐 보여주고 자동 닫힘
    } catch {
      setPendingConsent((c) => (c ? { ...c, saving: false } : c));
      alert("저장에 실패했습니다.");
    }
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
          if (m.aiResponse) pair.push({ id: `hist-${m.id}-assistant`, role: "assistant", content: m.aiResponse, promptSessionId: m.id });
          return pair;
        });
        setMessages(loaded);

        // 이미 만족도를 남긴 메시지는 새로고침해도 버튼이 다시 안 뜨도록 서버 값으로 초기화
        const initialSatisfaction: Record<string, "good" | "bad"> = {};
        for (const m of history) {
          if (m.satisfaction === "good" || m.satisfaction === "bad") {
            initialSatisfaction[`hist-${m.id}-assistant`] = m.satisfaction;
          }
        }
        setSatisfaction(initialSatisfaction);
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
      const assistantId = generateId();
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: resultText, promptSessionId: res?.promptSessionId },
      ]);

      // 수신자 이름이 감지됐고, 이미 저장 동의를 한 상태가 아니면 동의 카드 노출
      // (프로필이 없으면 당연히 미동의 상태, 있으면 실제 동의 기록을 조회해서 판단)
      const detected = detectReceiverName(prompt);
      if (detected) {
        const existing = receiverProfiles.find((p) => p.receiverName === detected);
        try {
          const allowed = existing ? await getConsentStatus(existing.id) : false;
          if (!allowed) {
            setPendingConsent({ name: detected, forMessageId: assistantId, saving: false, done: false });
          }
        } catch {
          // 동의 상태 조회 실패 시, 놓치는 것보다 한 번 더 물어보는 쪽이 안전해서 카드 노출
          setPendingConsent({ name: detected, forMessageId: assistantId, saving: false, done: false });
        }
      }

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
    setPendingConsent(null); // 새 메시지 보내면 이전 턴의 동의 카드는 정리
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

                  {m.promptSessionId != null && (
                    <div className="satisfaction-row">
                      {satisfaction[m.id] ? (
                        <span className="satisfaction-thanks">감사해요, 다음 추천에 반영할게요</span>
                      ) : (
                        <>
                          <span className="satisfaction-label">이 결과, 도움이 됐나요?</span>
                          <button
                            className="satisfaction-btn"
                            onClick={() => rateSatisfaction(m, "good")}
                            aria-label="도움이 됐어요"
                          >
                            👍
                          </button>
                          <button
                            className="satisfaction-btn"
                            onClick={() => rateSatisfaction(m, "bad")}
                            aria-label="도움이 안 됐어요"
                          >
                            👎
                          </button>
                        </>
                      )}
                    </div>
                  )}

                  {pendingConsent && pendingConsent.forMessageId === m.id && (
                    <div className="consent-card">
                      {pendingConsent.done ? (
                        <span className="consent-done">저장했어요, 다음 추천에 반영할게요</span>
                      ) : (
                        <>
                          <div className="consent-title">수신자 프로필 감지</div>
                          <div className="consent-name">{pendingConsent.name}</div>

                          {/* TODO: (목업) 실제 스타일 분석 붙으면 MOCK_STYLE_HINTS 제거하고 이 블록 교체 */}
                          <ul className="consent-hints">
                            {MOCK_STYLE_HINTS.map((hint) => (
                              <li key={hint}>{hint}</li>
                            ))}
                          </ul>
                          <div className="consent-mock-note">
                            ※ 아래는 예시입니다. 실제 스타일 분석 기능은 아직 없어요.
                          </div>

                          <div className="consent-question">
                            앞으로 <b>{pendingConsent.name}</b> 기본 스타일로 저장할까요?
                          </div>
                          <div className="consent-actions">
                            <button
                              className="consent-apply"
                              onClick={applyConsent}
                              disabled={pendingConsent.saving}
                            >
                              {pendingConsent.saving ? "저장 중…" : "앞으로 적용"}
                            </button>
                            <button
                              className="consent-dismiss"
                              onClick={() => setPendingConsent(null)}
                              disabled={pendingConsent.saving}
                            >
                              저장 안 함
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  )}
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