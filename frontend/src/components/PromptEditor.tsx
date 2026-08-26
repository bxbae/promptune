"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { analyze, execute, recordBehaviorAction, type AnalyzeResponse } from "@/lib/api";
import { uploadDocument, type DocumentItem } from "@/api/documents";

interface ElementUiMeta {
  label: string;
  question: string;
}

const ELEMENT_UI: Record<string, ElementUiMeta> = {
  TASK: {
    label: "요청할 작업을 조금 더 명확히 하면 좋아요",
    question: "무엇을 해드리면 될까요?",
  },
  AUDIENCE: {
    label: "결과물을 볼 대상이 더 명확하면 좋아요",
    question: "누구를 위한 결과물인가요?",
  },
  CONTEXT: {
    label: "업무 배경이나 목적이 조금 더 필요해요",
    question: "어떤 상황이나 목적으로 사용하는 건가요?",
  },
  FORMAT: {
    label: "원하는 출력 형식을 지정하면 좋아요",
    question: "어떤 형식으로 작성할까요?",
  },
  TONE: {
    label: "말투나 문체를 지정하면 좋아요",
    question: "어떤 어조로 작성할까요?",
  },
  LENGTH: {
    label: "원하는 분량을 지정하면 좋아요",
    question: "어느 정도 길이로 작성할까요?",
  },
  CONSTRAINT: {
    label: "지켜야 할 조건을 추가하면 좋아요",
    question: "반드시 지켜야 할 조건이 있나요?",
  },
  EXAMPLE: {
    label: "참고할 예시가 있으면 결과가 더 정확해져요",
    question: "참고할 예시나 형태가 있나요?",
  },
};

// 사용자가 AI 추천 대신 직접 입력해서 보완한 요소 기록.
// 기존 onSubmit(text, directEdits) 계약을 유지한다.
export interface DirectEdit {
  element: string;
  generated: string;
  userFinal: string;
}

interface PromptEditorProps {
  onSubmit?: (
    displayText: string,
    directEdits: DirectEdit[],
    sentAttachments: DocumentItem[],
    // 실제로 AI에 보내는 텍스트(인용 블록·파일만 첨부 시 기본 지시문 포함).
    // 없으면 displayText를 그대로 전송용으로도 사용.
    sendText?: string,
  ) => void;
  compact?: boolean;
  disabled?: boolean;
  placeholder?: string;
  chatSessionId?: number;
  // 이전 메시지를 인용해서 다음 프롬프트에 맥락으로 참고시킬 때 사용.
  quotedMessage?: { role: "user" | "assistant"; content: string } | null;
  onClearQuote?: () => void;
}

type AttachmentState = {
  key: string;
  name: string;
  status: "uploading" | "done" | "error";
  doc?: DocumentItem;
};

export default function PromptEditor({
  onSubmit,
  compact = false,
  disabled = false,
  placeholder,
  chatSessionId,
  quotedMessage,
  onClearQuote,
}: PromptEditorProps = {}) {
  const [text, setText] = useState("");
  const [resolved, setResolved] = useState<Set<string>>(new Set());
  const directEditsRef = useRef<DirectEdit[]>([]);

  const [optIdx, setOptIdx] = useState(0);
  const [customOpen, setCustomOpen] = useState(false);
  const [customValue, setCustomValue] = useState("");

  const [gate, setGate] = useState<{
    passed: boolean;
    reason: string;
  } | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResponse | null>(
    null,
  );
  const [analyzing, setAnalyzing] = useState(false);

  const [result, setResult] = useState("");
  const [sending, setSending] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const submittingRef = useRef(false);
  // 한글 (조합형 입력) 중 Enter로 오전송되는 것 방지 플래그.
  // macOS IME는 마지막 글자 확정 전에 keydown(Enter)이 먼저 발생할 수 있어서 조합이 끝났는지 여기서 직접 추적.
  const isComposingRef = useRef(false);

  const [attachments, setAttachments] = useState<AttachmentState[]>([]);

  // 파일을 선택한 즉시 전송 버튼을 누를 수 있게 하되, 실제 전송은
  // 업로드/인덱싱이 끝난 뒤 진행한다.
  // 기존 구현은 status=done일 때만 전송 버튼을 활성화해서 업로드가
  // 오래 걸리면 사용자가 텍스트를 입력해야만 보낼 수 있는 것처럼 보였다.
  const uploadTasksRef = useRef<Map<string, Promise<DocumentItem | null>>>(
    new Map(),
  );
  const uploadedDocsRef = useRef<Map<string, DocumentItem>>(new Map());

  // 파일 드래그앤드롭 (input-wrap 전체가 드롭존).
  // dragCounterRef: input-wrap 안 자식(textarea/overlay/popup 등) 경계를
  // 넘나들 때마다 발생하는 dragEnter/dragLeave로 isDragOver가 깜빡이는 것을 방지.
  const [isDragOver, setIsDragOver] = useState(false);
  const dragCounterRef = useRef(0);

  const activeSuggestion =
    analysisResult?.suggest?.suggestions.find(
      (suggestion) => !resolved.has(suggestion.element),
    ) ?? null;

  const activeElement = activeSuggestion?.element ?? null;

  const activeMeta = activeElement
    ? (ELEMENT_UI[activeElement] ?? {
        label: `${activeElement} 요소를 보완하면 좋아요`,
        question: "어떤 내용을 추가할까요?",
      })
    : null;

  const activeOptions = activeSuggestion
    ? [activeSuggestion.primary, ...activeSuggestion.alternatives].filter(
        (option, index, array) =>
          option.trim().length > 0 && array.indexOf(option) === index,
      )
    : [];

  const scheduleAnalyze = useCallback((value: string) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

    setGate(null);
    setAnalysisResult(null);
    setOptIdx(0);
    setCustomOpen(false);
    setCustomValue("");

    if (!value.trim()) {
      setAnalyzing(false);
      return;
    }

    timerRef.current = setTimeout(async () => {
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      try {
        setAnalyzing(true);
        const response = await analyze(value, ctrl.signal);

        if (abortRef.current !== ctrl) {
          return;
        }

        setGate(response.gate);
        setAnalysisResult(response);
      } catch (error: unknown) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        console.error("프롬프트 분석 실패:", error);

        if (abortRef.current === ctrl) {
          setGate(null);
          setAnalysisResult(null);
        }
      } finally {
        if (abortRef.current === ctrl) {
          abortRef.current = null;
          setAnalyzing(false);
        }
      }
    }, 800);
  }, []);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  // 사용자가 드롭존(input-wrap) 밖에서 파일을 놓치면 브라우저가 그 파일을
  // 새 탭으로 열어버리므로, window 레벨에서도 기본 동작을 막아준다.
  useEffect(() => {
    const preventDefault = (e: DragEvent) => e.preventDefault();

    window.addEventListener("dragover", preventDefault);
    window.addEventListener("drop", preventDefault);

    return () => {
      window.removeEventListener("dragover", preventDefault);
      window.removeEventListener("drop", preventDefault);
    };
  }, []);

  // 프롬프트가 길어질수록 textarea 높이를 내용에 맞게 늘려준다.
  // compact(대화 중 하단 컴포저)와 홈 화면 컴포저는 허용 높이를 다르게 둔다.
  // overlay는 mirror-div라 textarea와 정확히 같은 높이/스크롤 위치를 유지해야
  // 밑줄 위치가 어긋나지 않는다.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;

    const maxHeight = compact ? 160 : 320;

    el.style.height = "auto";
    const nextHeight = Math.min(el.scrollHeight, maxHeight);
    el.style.height = `${nextHeight}px`;

    if (overlayRef.current) {
      overlayRef.current.style.height = `${nextHeight}px`;
      overlayRef.current.scrollTop = el.scrollTop;
    }
  }, [text, compact]);

  function applySuggestion(value: string, isCustom = false) {
    if (!activeElement) {
      return;
    }

    const trimmedValue = value.trim();
    if (!trimmedValue) {
      return;
    }

    if (isCustom) {
      directEditsRef.current.push({
        element: activeElement,
        generated: activeOptions.join(" / "),
        userFinal: trimmedValue,
      });
    }

    recordBehaviorAction(activeElement, "applied", chatSessionId).catch(() => {
      // 행동 기록 실패는 채팅 흐름을 막지 않음 (조용히 무시)
    });

    const nextText = mergePromptWithSuggestion(text, trimmedValue);

    setResolved((prev) => {
      const updated = new Set(prev);
      updated.add(activeElement);
      return updated;
    });

    setText(nextText);
    setOptIdx(0);
    setCustomOpen(false);
    setCustomValue("");

    scheduleAnalyze(nextText);
  }

  function skipActiveSuggestion() {
    if (!activeElement) {
      return;
    }

    recordBehaviorAction(activeElement, "rejected", chatSessionId).catch(() => {
      // 행동 기록 실패는 채팅 흐름을 막지 않음 (조용히 무시)
    });

    setResolved((prev) => {
      const updated = new Set(prev);
      updated.add(activeElement);
      return updated;
    });

    setOptIdx(0);
    setCustomOpen(false);
    setCustomValue("");
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (activeSuggestion && !customOpen) {
      if (e.key === "Tab") {
        e.preventDefault();
        const option = activeOptions[optIdx];
        if (option) {
          applySuggestion(option);
        }
        return;
      }

      if (e.key === "Escape") {
        e.preventDefault();
        skipActiveSuggestion();
        return;
      }

      if (e.key === "ArrowDown" && activeOptions.length > 0) {
        e.preventDefault();
        setOptIdx((index) => Math.min(activeOptions.length - 1, index + 1));
        return;
      }

      if (e.key === "ArrowUp" && activeOptions.length > 0) {
        e.preventDefault();
        setOptIdx((index) => Math.max(0, index - 1));
        return;
      }
    }

    if (e.key === "Enter" && !e.shiftKey) {
      // 한글 등 조합 중(예: 마지막 글자가 아직 확정 안 됨)인 Enter는 전송 트리거로 취급하지 않는다.
      // ref와 nativeEvent.isComposing을 둘 다 체크하는 이유:
      // 브라우저별로 "조합 확정 순간의 Enter"에 isComposing 값이 다르게 찍히는 경우가 있어서
      // 하나만 믿으면 여전히 새는 케이스가 생김.
      if (isComposingRef.current || e.nativeEvent.isComposing) {
        return;
      }

      e.preventDefault();
      void onExecute();
    }
  }

  function mergePromptWithSuggestion(text: string, suggestion: string): string {
    let base = text.trim();
    const addition = suggestion.trim();

    if (base && !/[.!?。！？]$/.test(base)) {
      base = `${base}.`;
    }

    return `${base} ${addition}`.trim();
  }

  async function handleFilesSelected(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) {
      return;
    }

    const files = Array.from(fileList);

    for (const file of files) {
      const key = `${file.name}-${Date.now()}-${Math.random()
        .toString(36)
        .slice(2, 7)}`;

      setAttachments((prev) => [
        ...prev,
        { key, name: file.name, status: "uploading" },
      ]);

      // 업로드를 여기서 await하지 않는다. 여러 파일은 병렬로 올리고,
      // 사용자가 먼저 전송을 눌렀다면 onExecute()가 이 Promise를 기다린다.
      const task = uploadDocument(
        file,
        file.name,
        "기타",
        undefined,
      )
        .then((doc) => {
          if (
            doc.indexStatus &&
            !["READY", "TEXT_READY"].includes(doc.indexStatus)
          ) {
            throw new Error(
              doc.indexStatus === "FAILED"
                ? `파일 분석에 실패했습니다: ${doc.indexError || file.name}`
                : `파일이 아직 분석 준비 중입니다: ${file.name}`,
            );
          }

          uploadedDocsRef.current.set(key, doc);

          setAttachments((prev) =>
            prev.map((attachment) =>
              attachment.key === key
                ? { ...attachment, status: "done", doc }
                : attachment,
            ),
          );

          return doc;
        })
        .catch((error) => {
          console.error("문서 업로드 실패:", error);

          setAttachments((prev) =>
            prev.map((attachment) =>
              attachment.key === key
                ? { ...attachment, status: "error" }
                : attachment,
            ),
          );

          return null;
        })
        .finally(() => {
          uploadTasksRef.current.delete(key);
        });

      uploadTasksRef.current.set(key, task);
    }

    // 같은 파일을 다시 선택해도 onChange가 다시 발생하도록 즉시 초기화한다.
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function removeAttachment(key: string) {
    uploadedDocsRef.current.delete(key);
    uploadTasksRef.current.delete(key);

    setAttachments((prev) =>
      prev.filter((attachment) => attachment.key !== key),
    );
  }

  function resetEditor() {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

    setText("");
    setResolved(new Set());
    directEditsRef.current = [];
    setOptIdx(0);
    setCustomOpen(false);
    setCustomValue("");
    setGate(null);
    setAnalysisResult(null);
    setAnalyzing(false);
    setAttachments([]);
    uploadTasksRef.current.clear();
    uploadedDocsRef.current.clear();
  }

  async function onExecute() {
    const typedText = text.trim();
    const selectedAttachments = [...attachments];
    const hasSelectedAttachments = selectedAttachments.length > 0;
    const hasUploadCandidate = selectedAttachments.some(
      (attachment) => attachment.status !== "error",
    );

    // 파일을 막 선택해서 아직 uploading이어도 전송 요청 자체는 허용한다.
    // 실제 onSubmit은 아래에서 해당 업로드 Promise가 끝난 뒤 호출된다.
    if (
      (!typedText && !hasUploadCandidate) ||
      sending ||
      disabled ||
      submittingRef.current
    ) {
      return;
    }

    // 실패한 첨부를 조용히 빼고 텍스트만 보내면 사용자는 파일도 전달된
    // 것으로 오해한다. 실패 파일은 제거/재첨부하기 전까지 전송하지 않는다.
    if (selectedAttachments.some((attachment) => attachment.status === "error")) {
      window.alert(
        "첨부파일 업로드에 실패했습니다. 실패한 파일을 제거한 뒤 다시 첨부해주세요.",
      );
      return;
    }

    submittingRef.current = true;

    try {
      const selectedKeys = selectedAttachments.map((attachment) => attachment.key);
      const pendingUploads = selectedKeys
        .map((key) => uploadTasksRef.current.get(key))
        .filter(
          (task): task is Promise<DocumentItem | null> => Boolean(task),
        );

      if (pendingUploads.length > 0) {
        // 버튼을 누른 뒤에는 중복 전송을 막고, 현재 업로드/인덱싱이
        // 완료되는 즉시 같은 클릭으로 채팅 전송까지 이어간다.
        setSending(true);
        await Promise.all(pendingUploads);
      }

      const sentAttachments = selectedKeys
        .map((key) => uploadedDocsRef.current.get(key))
        .filter((doc): doc is DocumentItem => Boolean(doc));

      // 첨부를 선택했는데 하나라도 최종 업로드에 실패했다면 텍스트만
      // 전송하지 않는다. 파일이 빠진 채 질문되는 기존 문제를 막는다.
      if (
        hasSelectedAttachments &&
        sentAttachments.length !== selectedAttachments.length
      ) {
        window.alert(
          "첨부파일 준비가 완료되지 않았습니다. 잠시 후 다시 시도하거나 실패한 파일을 다시 첨부해주세요.",
        );
        return;
      }

      // 텍스트 없이 파일만 첨부한 경우에도 정상적인 문서 읽기 요청으로 보낸다.
      const baseText = typedText || "첨부된 파일의 내용을 읽고 핵심 내용을 알려주세요.";

      // 인용된 이전 메시지가 있으면 입력창 표시 텍스트는 그대로 두고
      // AI에 보내는 finalPrompt에만 인용 블록을 붙인다.
      const finalPrompt = quotedMessage
        ? `[인용된 이전 ${quotedMessage.role === "user" ? "내 메시지" : "AI 응답"}]\n${quotedMessage.content}\n\n[위 내용을 참고해서 답변]\n${baseText}`
        : baseText;

      if (onSubmit) {
        onSubmit(
          typedText,
          [...directEditsRef.current],
          sentAttachments,
          finalPrompt,
        );
        resetEditor();
        onClearQuote?.();
        return;
      }

      setSending(true);

      try {
        const response = await execute(finalPrompt);
        setResult(response?.result?.result ?? JSON.stringify(response));
        onClearQuote?.();
      } catch (error) {
        console.error("프롬프트 실행 실패:", error);
        setResult("요청 실행 중 오류가 발생했습니다.");
      }
    } finally {
      setSending(false);
      setTimeout(() => {
        submittingRef.current = false;
      }, 0);
    }
  }

  const gateBlocked = Boolean(gate && !gate.passed);
  const targetElements = analysisResult?.recommend?.targetElements ?? [];
  const missing = analysisResult?.diagnose?.missing ?? {};
  const typoCount = analysisResult?.diagnose?.typos?.length ?? 0;

  return (
    <div className={`composer-wrap ${compact ? "compact" : ""}`}>
      {!compact && (
        <h1 className="composer-heading">오늘은 뭘 다듬어볼까요?</h1>
      )}

      <div className="composer-box">
        {quotedMessage && (
          <div className="quote-preview">
            <div className="quote-preview-body">
              <span className="quote-preview-label">
                {quotedMessage.role === "user" ? "내 메시지 인용" : "AI 응답 인용"}
              </span>
              <span className="quote-preview-text">{quotedMessage.content}</span>
            </div>
            <button
              type="button"
              className="quote-preview-close"
              onClick={() => onClearQuote?.()}
              aria-label="인용 취소"
            >
              ×
            </button>
          </div>
        )}
        <div
          className={`input-wrap ${isDragOver ? "drag-over" : ""}`}
          onDragEnter={(e) => {
            e.preventDefault();
            if (disabled) return;
            dragCounterRef.current += 1;
            setIsDragOver(true);
          }}
          onDragOver={(e) => {
            // 필수: 이게 없으면 onDrop 자체가 브라우저에서 안 잡힘
            e.preventDefault();
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            dragCounterRef.current -= 1;
            if (dragCounterRef.current <= 0) {
              dragCounterRef.current = 0;
              setIsDragOver(false);
            }
          }}
          onDrop={(e) => {
            e.preventDefault();
            dragCounterRef.current = 0;
            setIsDragOver(false);
            if (disabled) return;
            void handleFilesSelected(e.dataTransfer.files);
          }}
        >
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => {
              const value = e.target.value;
              setText(value);
              scheduleAnalyze(value);
            }}
            onCompositionStart={() => {
              isComposingRef.current = true;
            }}
            onCompositionEnd={() => {
              isComposingRef.current = false;
            }}
            onKeyDown={onKeyDown}
            onScroll={(e) => {
              // 캡(maxHeight)에 도달해 내부 스크롤이 생기면
              // overlay(밑줄 레이어)도 같은 스크롤 위치를 따라가야 함
              if (overlayRef.current) {
                overlayRef.current.scrollTop = e.currentTarget.scrollTop;
              }
            }}
            placeholder={placeholder ?? "보내기 전에 먼저 다듬어드려요"}
            rows={1}
          />
          {/* textarea와 완전히 겹치는 오버레이(mirror-div 기법)로 밑줄만 그려줌.
              font-size/line-height/padding이 textarea와 정확히 같아야 줄바꿈 위치가 어긋나지 않음(globals.css 참고).
              백엔드가 정확한 글자 위치(span)를 안 줘서, 지금은 "부족한 요소가 있으면 프롬프트 전체"에 밑줄. */}
          <div className="overlay" ref={overlayRef} aria-hidden="true">
            {activeElement ? (
              <span className="ov-underline-word">{text}</span>
            ) : (
              text
            )}
          </div>

          {/* 밑줄(=지금은 입력창 전체) 바로 위에 뜨는 플로팅 카드.
              .input-wrap이 position:relative라 이 카드는 그 기준으로 절대 위치. */}
        {activeSuggestion && activeMeta && (
            <div
              className="ai-suggestion-card"
              role="region"
              aria-label={`${activeElement ?? ""} 요소 추천`}
            >
              <div className="popup-label">
                <span className="popup-dot" />
                {activeMeta.label}
              </div>

              <div className="popup-question">{activeMeta.question}</div>

              {activeOptions.map((option, index) => (
                <button
                  key={`${activeElement}-${option}`}
                  type="button"
                  className={`popup-option ${
                    index === optIdx && !customOpen ? "active" : ""
                  }`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    applySuggestion(option);
                  }}
                  onMouseEnter={() => setOptIdx(index)}
                >
                  {option}
                </button>
              ))}

              {!customOpen ? (
                <button
                  type="button"
                  className="popup-custom-btn"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    setCustomOpen(true);
                  }}
                >
                  직접 입력
                </button>
              ) : (
                <input
                  className="popup-custom-input"
                  autoFocus
                  value={customValue}
                  onChange={(e) => setCustomValue(e.target.value)}
                  onKeyDown={(e) => {
                    e.stopPropagation();

                    if (e.key === "Enter") {
                      e.preventDefault();
                      applySuggestion(customValue, true);
                    }

                    if (e.key === "Escape") {
                      e.preventDefault();
                      setCustomOpen(false);
                      setCustomValue("");
                    }
                  }}
                  placeholder="직접 입력 후 Enter"
                />
              )}

              <button
                type="button"
                className="popup-custom-btn"
                onMouseDown={(e) => {
                  e.preventDefault();
                  skipActiveSuggestion();
                }}
              >
                이 요소는 건너뛰기
              </button>
            </div>
          )}
        </div>

        {attachments.length > 0 && (
          <div className="attach-chip-row">
            {attachments.map((attachment) => (
              <div
                key={attachment.key}
                className={`attach-chip ${attachment.status}`}
              >
                <span className="attach-chip-name" title={attachment.name}>
                  {attachment.name}
                </span>

                {attachment.status === "uploading" && (
                  <span className="attach-chip-status">파일 준비 중…</span>
                )}

                {attachment.status === "error" && (
                  <span className="attach-chip-status">실패</span>
                )}

                <button
                  type="button"
                  className="attach-chip-remove"
                  onClick={() => removeAttachment(attachment.key)}
                  aria-label="첨부 제거"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="composer-actions">
          <div className="composer-icons">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              multiple
              hidden
              onChange={(e) => {
                void handleFilesSelected(e.target.files);
              }}
            />

            <button
              className="icon-btn"
              type="button"
              title="파일 첨부"
              onClick={() => fileInputRef.current?.click()}
            >
              <img src="/icons/plus-muted.png" alt="" />
            </button>

            <button className="icon-btn" type="button" title="링크 (미구현)">
              <img src="/icons/link.png" alt="" />
            </button>
          </div>

          <div className="composer-right">
            <span className="char-analyzing">{analyzing && "분석 중…"}</span>

            <button
              className="send-btn"
              disabled={
                (!text.trim() &&
                  !attachments.some((a) => a.status !== "error")) ||
                sending ||
                disabled
              }
              onClick={() => {
                void onExecute();
              }}
              title="Enter로도 실행됩니다"
            >
              ↑
            </button>
          </div>
        </div>
      </div>

      {!compact && (
        <div className="hint">
          <b>왜 이렇게 표시되나요?</b> KcELECTRA가 프롬프트의 8요소 충족 여부를
          진단하고, 보완이 필요한 요소 중 우선순위가 높은 항목에 대해 추천
          문구를 제안해요.
        </div>
      )}

      {analysisResult?.diagnose && !gateBlocked && (
        <div className="prompt-analysis-summary">
          <span>
            보완 필요:{" "}
            {Object.values(missing).filter((value) => value === 1).length}개
          </span>

          {targetElements.length > 0 && (
            <span> · 우선 추천: {targetElements.join(", ")}</span>
          )}

          {typoCount > 0 && <span> · 오탈자 후보: {typoCount}개</span>}
        </div>
      )}

      {gateBlocked && <div className="gate-block">⚠ {gate?.reason}</div>}

      {result && (
        <div className="result">
          <label className="eyebrow">생성 결과</label>
          <pre>{result}</pre>
        </div>
      )}
    </div>
  );
}
