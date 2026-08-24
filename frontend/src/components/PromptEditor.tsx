"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { analyze, execute, type AnalyzeResponse } from "@/lib/api";
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
  const submittingRef = useRef(false);

  const [attachments, setAttachments] = useState<AttachmentState[]>([]);

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
  const targetElements = analysisResult?.recommend?.targetElements ?? [];
  const missing = analysisResult?.diagnose?.missing ?? {};
  const typoCount = analysisResult?.diagnose?.typos?.length ?? 0;

  return (
    <div className="composer-wrap">
      {!compact && (
        <h1 className="composer-heading">오늘은 뭘 다듬어볼까요?</h1>
      )}

      <div className="composer-box">
        <div className="input-wrap">
          <textarea
            value={text}
            onChange={(e) => {
              const value = e.target.value;
              setText(value);
              scheduleAnalyze(value);
            }}
            onKeyDown={onKeyDown}
            placeholder={placeholder ?? "보내기 전에 먼저 다듬어드려요"}
            rows={compact ? 1 : 2}
          />
        </div>

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
