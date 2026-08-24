"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  analyze,
  execute,
  recordBehaviorAction,
  type AnalyzeResponse,
} from "@/lib/api";
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
  onSubmit?: (text: string, directEdits: DirectEdit[]) => void;
  compact?: boolean;
  disabled?: boolean;
  placeholder?: string;
  chatSessionId?: number;
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

  const [attachments, setAttachments] = useState<AttachmentState[]>([]);

  // 파일 드래그앤드롭 (input-wrap 전체가 드롭존).
  // dragCounterRef: input-wrap 안 자식(textarea/overlay/popup 등) 경계를
  // 넘나들 때마다 발생하는 dragEnter/dragLeave로 isDragOver가 깜빡이는 것을 방지.
  const [isDragOver, setIsDragOver] = useState(false);
  const dragCounterRef = useRef(0);

  const targetElements = analysisResult?.recommend?.targetElements ?? [];

  const activeElement =
    targetElements.find((element) => !resolved.has(element)) ?? null;

  const activeSuggestion = activeElement
    ? (analysisResult?.suggest?.suggestions.find(
        (suggestion) => suggestion.element === activeElement,
      ) ?? null)
    : null;

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
    const descriptionAtAttach = text.trim() || undefined;

    for (const file of files) {
      const key = `${file.name}-${Date.now()}-${Math.random()
        .toString(36)
        .slice(2, 7)}`;

      setAttachments((prev) => [
        ...prev,
        { key, name: file.name, status: "uploading" },
      ]);

      try {
        const doc = await uploadDocument(
          file,
          file.name,
          "기타",
          descriptionAtAttach,
        );

        setAttachments((prev) =>
          prev.map((attachment) =>
            attachment.key === key
              ? { ...attachment, status: "done", doc }
              : attachment,
          ),
        );
      } catch (error) {
        console.error("문서 업로드 실패:", error);
        setAttachments((prev) =>
          prev.map((attachment) =>
            attachment.key === key
              ? { ...attachment, status: "error" }
              : attachment,
          ),
        );
      }
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function removeAttachment(key: string) {
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
  }

  async function onExecute() {
    const finalPrompt = text.trim();

    if (!finalPrompt || sending || disabled) {
      return;
    }

    if (onSubmit) {
      if (submittingRef.current) {
        return;
      }

      submittingRef.current = true;

      try {
        onSubmit(finalPrompt, [...directEditsRef.current]);
        resetEditor();
      } finally {
        setTimeout(() => {
          submittingRef.current = false;
        }, 0);
      }

      return;
    }

    setSending(true);

    try {
      const response = await execute(finalPrompt);
      setResult(response?.result?.result ?? JSON.stringify(response));
    } catch (error) {
      console.error("프롬프트 실행 실패:", error);
      setResult("요청 실행 중 오류가 발생했습니다.");
    } finally {
      setSending(false);
    }
  }

  const gateBlocked = Boolean(gate && !gate.passed);
  const missing = analysisResult?.diagnose?.missing ?? {};
  const typoCount = analysisResult?.diagnose?.typos?.length ?? 0;

  return (
    <div className={`composer-wrap ${compact ? "compact" : ""}`}>
      {!compact && (
        <h1 className="composer-heading">오늘은 뭘 다듬어볼까요?</h1>
      )}

      <div className="composer-box">
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
          {activeElement && activeMeta && (
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
                  <span className="attach-chip-status">업로드 중…</span>
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
              disabled={!text.trim() || sending || disabled}
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
