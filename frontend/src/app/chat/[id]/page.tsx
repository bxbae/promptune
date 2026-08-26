"use client";
import { useState, useRef, useEffect } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { execute } from "@/lib/api";
import { getChatMessages, MessageAttachment } from "@/api/chatSessions";
import { listReceiverProfiles, upsertReceiverProfile, ReceiverProfile } from "@/api/receiverProfiles";
import { microsoftMembers } from "@/lib/microsoft";
import { suggestToneFromJobTitle } from "@/lib/toneMapping";
import { grantConsent, getConsentStatus } from "@/api/consents";
import { submitPromptSessionEdit } from "@/api/promptSessions";
import PromptEditor, { DirectEdit } from "@/components/PromptEditor";
import { generateDocumentFile, type DocumentFormat, type DocumentItem } from "@/api/documents";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  promptSessionId?: number;
  // 방금 보낸 메시지는 DocumentItem[](업로드 응답), 지난 대화 다시 불러온 메시지는
  // MessageAttachment[](백엔드 /messages 응답)이 들어옴. 렌더링엔 id/title만 쓰여서
  // DocumentItem이 구조적으로 MessageAttachment를 만족하므로 타입 호환됨.
  attachments?: MessageAttachment[];
  // 실패한 응답에만 채워짐. "재전송" 버튼이 이 payload로 runAssistant를 다시 호출.
  failed?: boolean;
  retryPayload?: {
    prompt: string;
    directEdits: DirectEdit[];
    attachments: DocumentItem[];
  };
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

export default function ChatThreadPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const chatSessionId = Number(params.id);
  const isFresh = searchParams.get("run") === "1";  // /chat(새 채팅)에서 막 넘어온 경우

  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
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
      .catch(() => { }); // 실패해도 채팅 자체는 그대로 진행 (동의 카드만 안 뜸)
  }, []);

  // 만족도(👍/👎) - 메시지 id별로 선택 상태 기록 (한 번 누르면 고정, 재선택 불가 - 스토리보드 기준)
  const [satisfaction, setSatisfaction] = useState<Record<string, "good" | "bad">>({});
  // 응답 복사 버튼 - 복사 직후 잠깐 체크 아이콘으로 바뀌었다가 원래대로 돌아옴
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const [documentGenerating, setDocumentGenerating] = useState<
    Record<string, DocumentFormat | null>
  >({});

  const [generatedDocuments, setGeneratedDocuments] = useState<
    Record<string, {
      fileName: string;
      format: DocumentFormat;
      blob: Blob;
    }>
  >({});
  // 이전 메시지를 인용해서 다음 프롬프트에 맥락으로 붙여보내기
  const [quotedMessage, setQuotedMessage] = useState<
    { role: "user" | "assistant"; content: string } | null
  >(null);

  function quoteMessage(m: Message) {
    setQuotedMessage({ role: m.role, content: m.content });
  }

  async function copyMessage(m: Message) {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(m.content);
      } else {
        // Clipboard API를 못 쓰는 환경(구형 브라우저·비보안 컨텍스트) 대비 폴백
        const textarea = document.createElement("textarea");
        textarea.value = m.content;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      setCopiedId(m.id);
      setTimeout(() => {
        setCopiedId((id) => (id === m.id ? null : id));
      }, 1500);
    } catch {
      alert("복사에 실패했습니다.");
    }
  }

  async function generateMessageDocument(
    m: Message,
    format: DocumentFormat,
  ) {
    const firstLine =
      m.content
        .split("\n")
        .map((line) => line.trim())
        .find(Boolean) ?? "PrompTune 생성 문서";

    const title = firstLine
      .replace(/^[#*\-\s]+/, "")
      .slice(0, 40);

    setDocumentGenerating((prev) => ({
      ...prev,
      [m.id]: format,
    }));

    try {
      const blob = await generateDocumentFile(
        title,
        m.content,
        format,
      );

      const safeTitle =
        title.replace(/[\\/:*?"<>|]/g, "_") ||
        "PrompTune_생성_문서";

      setGeneratedDocuments((prev) => ({
        ...prev,
        [m.id]: {
          fileName: `${safeTitle}.${format}`,
          format,
          blob,
        },
      }));
    } catch (e) {
      alert(
        e instanceof Error
          ? e.message
          : "문서 생성에 실패했습니다."
      );
    } finally {
      setDocumentGenerating((prev) => ({
        ...prev,
        [m.id]: null,
      }));
    }
  }

  function downloadGeneratedDocument(m: Message) {
    const file = generatedDocuments[m.id];
    if (!file) return;

    const url = URL.createObjectURL(file.blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = file.fileName;

    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
  }

  async function rateSatisfaction(m: Message, value: "good" | "bad") {
    if (satisfaction[m.id]) return;

    setSatisfaction((prev) => ({
      ...prev,
      [m.id]: value,
    }));

    if (!m.promptSessionId) return;

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

      // MS 조직도에서 같은 이름 동료 찾아서 직급 기반으로 톤 추천 (없으면 null, 기존과 동일 동작)
      let suggestedTone: string | null = null;
      try {
        const members = await microsoftMembers();
        const matched = members.find((m) => m.displayName === pendingConsent.name);
        if (matched) suggestedTone = suggestToneFromJobTitle(matched.jobTitle);
      } catch {
        // MS 연동 안 한 사용자거나 조회 실패 - 조용히 무시, null로 폴백 (기존 동작과 동일)
      }

      // 1) 수신자 프로필 등록/갱신 (없으면 새로 생김, 있으면 톤·길이 평균 갱신)
      const saved = await upsertReceiverProfile(
        pendingConsent.name,
        suggestedTone, // MS 조직도 매칭되면 자동 추천값, 안 되면 기존처럼 null (사용자가 나중에 수동 입력)
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
      const stored = sessionStorage.getItem(`chat-first-${chatSessionId}`);
      sessionStorage.removeItem(`chat-first-${chatSessionId}`);
      if (stored) {
        // /chat/page.tsx가 { text, sendText, directEdits, attachments } JSON으로 저장
        const { text: displayText, sendText, directEdits, attachments } = JSON.parse(stored) as {
          text: string;
          sendText?: string;
          directEdits: DirectEdit[];
          attachments?: DocumentItem[];
        };
        const userMessageId = generateId();
        setMessages([{ id: userMessageId, role: "user", content: displayText.trim(), attachments }]);
        runAssistant(sendText ?? displayText, directEdits, attachments ?? [], userMessageId);
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
          if (m.prompt) pair.push({ id: `hist-${m.id}-user`, role: "user", content: m.prompt, attachments: m.attachments });
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
  }, [messages, isGenerating]);

  async function runAssistant(
    prompt: string,
    directEdits: DirectEdit[] = [],
    attachments: DocumentItem[] = [],
    userMessageId?: string,
  ) {
    setIsGenerating(true);

    // 생성 전에 미리 수신자 감지 - 이미 저장된 프로필과 이름이 일치하면 그 톤을 생성에 반영
    const detectedBeforeGen = detectReceiverName(prompt);
    const matchedProfile = detectedBeforeGen
      ? receiverProfiles.find((p) => p.receiverName === detectedBeforeGen)
      : undefined;

    try {
      const documentIds = attachments.map((a) => a.id);
      const res = await execute(prompt, chatSessionId, documentIds, matchedProfile?.id);
      const resultText = res?.result?.result ?? JSON.stringify(res);
      const assistantId = generateId();

      const documentAction = res?.documentAction as
        | {
            type: "GENERATE_DOCUMENT";
            title: string;
            content: string;
            format: DocumentFormat;
            useExistingTemplate?: boolean;
          }
        | undefined;

      if (documentAction?.type === "GENERATE_DOCUMENT") {
        try {
          const blob = await generateDocumentFile(
            documentAction.title,
            documentAction.content,
            documentAction.format,
          );

          setGeneratedDocuments((prev) => ({
            ...prev,
            [assistantId]: {
              fileName: `${documentAction.title}.${documentAction.format}`,
              format: documentAction.format,
              blob,
            },
          }));

          setMessages((prev) => [
            ...prev,
            {
              id: assistantId,
              role: "assistant",
              content: resultText,
              promptSessionId: res?.promptSessionId,
            },
          ]);
        } catch (e) {
          setMessages((prev) => [
            ...prev,
            {
              id: assistantId,
              role: "assistant",
              content:
                e instanceof Error
                  ? `문서 생성에 실패했습니다: ${e.message}`
                  : "문서 생성에 실패했습니다.",
              promptSessionId: res?.promptSessionId,
            },
          ]);
        } finally {
          setIsGenerating(false);
        }

        window.dispatchEvent(
          new CustomEvent("chat-session-updated", {
            detail: { chatSessionId },
          })
        );

        return;
      }

      setIsGenerating(false);
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: resultText, promptSessionId: res?.promptSessionId },
      ]);

      // "직접 입력"으로 해결한 요소 = 직접수정. response_edits에 기록.
      // prompt_session DB컬럼 1개라 요소가 여러 개면 리스트를 못 넣음
      // >> 요소명 태그 붙여서 줄바꿈으로 다 합쳐 저장
      if (directEdits.length > 0 && res?.promptSessionId) {
        const generatedResult = directEdits.map((d) => `[${d.element}] ${d.generated}`).join("\n");
        const userFinalResult = directEdits.map((d) => `[${d.element}] ${d.userFinal}`).join("\n");
        submitPromptSessionEdit(res.promptSessionId, { generatedResult, userFinalResult }).catch(() => {
          // 직접수정 기록 실패는 채팅 흐름을 막지 않음 (조용히 무시, 콘솔에만 남김)
          console.error("직접수정 기록 저장 실패");
        });
      }

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
      setIsGenerating(false);
      setMessages((prev) => [
        ...prev.map((x) =>
          userMessageId && x.id === userMessageId
            ? { ...x, failed: true, retryPayload: { prompt, directEdits, attachments } }
            : x,
        ),
        {
          id: generateId(),
          role: "assistant",
          content: "결과를 생성하지 못했습니다. 잠시 후 다시 시도해주세요.",
        },
      ]);
    }
  }

  // 실패했던 프롬프트를 같은 payload로 다시 시도.
  // 이 프롬프트 바로 다음에 붙어있던 실패 안내 메시지들만 지우고,
  // user 메시지의 failed 표시는 낙관적으로 먼저 지운 뒤 재요청한다.
  function retryMessage(m: Message) {
    if (isGenerating || !m.retryPayload) return;

    setMessages((prev) => {
      const idx = prev.findIndex((x) => x.id === m.id);
      if (idx === -1) return prev;

      const next = [...prev];
      next[idx] = { ...next[idx], failed: false };

      let removeCount = 0;
      for (let i = idx + 1; i < next.length; i++) {
        if (next[i].role === "assistant" && !next[i].promptSessionId) {
          removeCount++;
        } else {
          break;
        }
      }
      if (removeCount > 0) {
        next.splice(idx + 1, removeCount);
      }

      return next;
    });

    const { prompt, directEdits, attachments } = m.retryPayload;
    runAssistant(prompt, directEdits, attachments, m.id);
  }

  function handleSubmit(
    displayText: string,
    directEdits: DirectEdit[],
    attachments: DocumentItem[],
    sendText?: string,
  ) {
    if (isGenerating) return;
    setPendingConsent(null); // 새 메시지 보내면 이전 턴의 동의 카드는 정리
    const userMessageId = generateId();
    setMessages((prev) => [
      ...prev,
      { id: userMessageId, role: "user", content: displayText.trim(), attachments },
    ]);
    runAssistant(sendText ?? displayText, directEdits, attachments, userMessageId);
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
                <div className="msg-user-col">
                  {m.attachments && m.attachments.length > 0 && (
                    <div className="msg-attach-row">
                      {m.attachments.map((doc) => (
                        <span className="attach-chip sent" key={doc.id} title={doc.title}>
                          <span className="attach-chip-name">{doc.title}</span>
                        </span>
                      ))}
                    </div>
                  )}
                  {(m.content || m.failed) && (
                    <div className="msg-user-line">
                      <div className="msg-user-actions">
                        {m.content && (
                          <button
                            type="button"
                            className="user-quote-btn"
                            onClick={() => quoteMessage(m)}
                            aria-label="이 메시지 인용"
                            title="이 메시지를 인용해서 다시 질문하기"
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="9 14 4 9 9 4" />
                              <path d="M20 20v-7a4 4 0 0 0-4-4H4" />
                            </svg>
                          </button>
                        )}
                        {m.failed && (
                          <button
                            type="button"
                            className="user-retry-btn"
                            onClick={() => retryMessage(m)}
                            disabled={isGenerating}
                            aria-label="다시 시도"
                            title="응답 생성에 실패했어요. 다시 시도하려면 클릭하세요."
                          >
                            재시도<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="1 4 1 10 7 10" />
                              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
                            </svg>
                          </button>
                        )}
                      </div>
                      {m.content && <div className="msg-bubble user">{m.content}</div>}
                    </div>
                  )}
                </div>
              ) : (
                <div className="msg-assistant">
                  <div className="msg-sender">PrompTune</div>
                  <div className="msg-assistant-row">
                    <div className="msg-bubble assistant">
                      {m.content}
                      <button
                        type="button"
                        className={`copy-btn ${copiedId === m.id ? "copied" : ""}`}
                        onClick={() => copyMessage(m)}
                        aria-label="응답 복사"
                        title={copiedId === m.id ? "복사됨" : "복사하기"}
                      >
                        {copiedId === m.id ? (
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        ) : (
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                          </svg>
                        )}
                      </button>
                    </div>
                    <button
                      type="button"
                      className="quote-btn"
                      onClick={() => quoteMessage(m)}
                      aria-label="이 응답 인용"
                      title="이 응답을 인용해서 다시 질문하기"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="9 14 4 9 9 4" />
                        <path d="M20 20v-7a4 4 0 0 0-4-4H4" />
                      </svg>
                    </button>
                  </div>

                      {generatedDocuments[m.id] && (
                        <div className="generated-file-card">
                          <div className="generated-file-icon">
                            📄
                          </div>

                          <div className="generated-file-info">
                            <div className="generated-file-name">
                              {generatedDocuments[m.id].fileName}
                            </div>
                            <div className="generated-file-type">
                              {generatedDocuments[m.id].format.toUpperCase()}
                            </div>
                          </div>

                          <button
                            type="button"
                            className="generated-file-download"
                            onClick={() => downloadGeneratedDocument(m)}
                          >
                            다운로드
                          </button>
                        </div>
                      )}

                  {m.promptSessionId != null && (
                    <div className="satisfaction-row">
                      {satisfaction[m.id] ? (
                        <span className="satisfaction-thanks">감사해요, 다음 추천에 반영할게요</span>
                      ) : (
                        <div className="satisfaction-pending">
                          <span className="satisfaction-label">이 결과, 도움이 됐나요?</span>
                          <button
                            className="satisfaction-btn"
                            onClick={() => rateSatisfaction(m, "good")}
                            aria-label="도움이 됐어요"
                          >
                            <img src="/icons/thumbs-up.png" alt="" />
                          </button>
                          |
                          <button
                            className="satisfaction-btn"
                            onClick={() => rateSatisfaction(m, "bad")}
                            aria-label="도움이 안 됐어요"
                          >
                            <img src="/icons/thumbs-down.png" alt="" />
                          </button>
                        </div>
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

          {isGenerating && (
            <div className="msg-assistant">
              <div className="msg-sender">PrompTune</div>
              <div className="status-box">
                <span className="loading-spinner" aria-hidden="true" />
                <span className="status-title">답변 생성 중<span className="dots">···</span></span>
              </div>
            </div>
          )}

          <div ref={threadEndRef} />
        </div>
      )}

      <PromptEditor
        onSubmit={handleSubmit}
        disabled={isGenerating || loadingHistory}
        compact
        placeholder="다음 프롬프트를 입력하세요"
        chatSessionId={chatSessionId}
        quotedMessage={quotedMessage}
        onClearQuote={() => setQuotedMessage(null)}
      />
    </div>
  )
}