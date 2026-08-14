"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { analyze, execute } from "@/lib/api";

/**
 * 모호성 규칙 (mock)
 * ------------------------------------------------------------
 * 실제로는 KcELECTRA가 문장을 분석해 "어떤 부분이 왜 모호한지"를
 * 좌표(span)까지 함께 돌려줘야 하는데, 지금 백엔드(/api/analyze)는
 * 요소별 충족 여부(0/1)만 주고 정확한 위치는 안 줍니다.
 * 그래서 화면(밑줄 표시 위치)만 프론트에서 임시로 흉내 냅니다.
 * → 백엔드가 span을 내려주기 시작하면 find() 부분만 교체하면 됩니다.
 */
interface AmbiguityRule {
  id: string;
  dependsOn?: string; // 이 규칙이 나타나려면 먼저 해결돼야 하는 규칙
  find: (text: string) => { match: string; index: number } | null;
  label: string;      // 팝업 상단 빨간 점 옆 문구
  question: string;   // 팝업의 굵은 질문
  options: string[];
}

// 백엔드 연결 전, 모호성 규칙을 프론트에서 임시로 정의
// "메일"이 들어가면 모호성으로 간주
const RULES: AmbiguityRule[] = [
  {
    id: "task",
    find: (t) => {
      const i = t.indexOf("메일");
      return i >= 0 ? { match: "메일", index: i } : null;
    },
    label: "무엇을 요청하는 메일인지 불명확해요",
    question: "어떤 내용의 메일인가요?",
    options: ["보고서 제출 요청 메일", "회의 일정 안내 메일"],
  },
  {
    id: "tone",
    dependsOn: "task",
    find: (t) => {
      if (/정중하게|친근하게/.test(t)) return null;
      const m = t.match(/(좀)\s*보내(줘|주세요|줄래)?/);
      if (!m || m.index === undefined) return null;
      return { match: m[1], index: m.index };
    },
    label: "어조·말투 조건이 불명확해요",
    question: "어떤 어조로 보낼까요?",
    options: ["정중하게", "친근하게"],
  },
];

interface PromptEditorProps {
  // 있으면: 전송 시 이 콜백만 호출하고 입력창 비움 (실행/결과 표시는 호출한 쪽 책임)
  // 없으면: 기존처럼 이 컴포넌트가 직접 execute() 호출 + 결과를 자기 아래에 표시
  onSubmit?: (text: string) => void;
  // true: 큰 제목/힌트문구 없이 입력창만 (대화 스레드 하단용)
  compact?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export default function PromptEditor({ onSubmit, compact = false, disabled = false, placeholder }: PromptEditorProps = {}) {
  const [text, setText] = useState("");
  const [resolved, setResolved] = useState<Set<string>>(new Set());
  const [optIdx, setOptIdx] = useState(0);
  const [customOpen, setCustomOpen] = useState(false);
  const [customValue, setCustomValue] = useState("");

  const [gate, setGate] = useState<{ passed: boolean; reason: string } | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState("");
  const [sending, setSending] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 지금 화면에 떠 있어야 할 모호성 규칙 (한 번에 하나만)
  const activeRule = RULES.find(
    (r) =>
      !resolved.has(r.id) &&
      (!r.dependsOn || resolved.has(r.dependsOn)) &&
      r.find(text)
  );
  const match = activeRule ? activeRule.find(text) : null;

  // 0.7~1초 입력 중단 감지 → 실제 백엔드 진단 호출 (게이트 검사용)
  const scheduleAnalyze = useCallback((value: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (abortRef.current) abortRef.current.abort();
    if (!value.trim()) { setGate(null); return; }
    timerRef.current = setTimeout(async () => {
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      try {
        setAnalyzing(true);
        const res = await analyze(value, ctrl.signal);
        setGate(res.gate);
      } catch (e: any) {
        if (e.name !== "AbortError") console.error(e);
      } finally {
        setAnalyzing(false);
      }
    }, 800);
  }, []);

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (abortRef.current) abortRef.current.abort();
  }, []);

  // 오버레이(밑줄 표시용 div)와 textarea의 스크롤 위치를 항상 맞춰줌
  function syncScroll() {
    if (overlayRef.current && textareaRef.current) {
      overlayRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  }

  function applyOption(value: string) {
    if (!activeRule || !match) return;
    const next = text.slice(0, match.index) + value + text.slice(match.index + match.match.length);
    setText(next);
    setResolved((prev) => new Set(prev).add(activeRule.id));
    setOptIdx(0);
    setCustomOpen(false);
    setCustomValue("");
    scheduleAnalyze(next);
  }

  function skipActiveRule() {
    if (!activeRule) return;
    setResolved((prev) => new Set(prev).add(activeRule.id));
    setOptIdx(0);
    setCustomOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (activeRule && !customOpen) {
      if (e.key === "Tab") {
        e.preventDefault();
        applyOption(activeRule.options[optIdx]);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        skipActiveRule();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setOptIdx((i) => Math.min(activeRule.options.length - 1, i + 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setOptIdx((i) => Math.max(0, i - 1));
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onExecute();
    }
  }

  async function onExecute() {
    if (!text.trim() || sending || disabled) return;
    if (onSubmit) {
      onSubmit(text.trim());
      setText("");
      setResolved(new Set());
      setGate(null);
      setCustomOpen(false);
      return;
    }
    setSending(true);
    try {
      const res = await execute(text);
      setResult(res?.result?.result ?? JSON.stringify(res));
    } finally {
      setSending(false);
    }
  }

  // 오버레이용: 텍스트를 [이전 | 모호한 구간(밑줄) | 이후] 로 쪼갬
  let before = text, underline = "", after = "";
  if (activeRule && match) {
    before = text.slice(0, match.index);
    underline = match.match;
    after = text.slice(match.index + match.match.length);
  }

  const gateBlocked = gate && !gate.passed;

  return (
    <div className="composer-wrap">
      {!compact && <h1 className="composer-heading">오늘은 뭘 다듬어볼까요?</h1>}

      <div className="composer-box">
        <div className="input-wrap">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => { setText(e.target.value); scheduleAnalyze(e.target.value); }}
            onScroll={syncScroll}
            onKeyDown={onKeyDown}
            placeholder={placeholder ?? "보내기 전에 먼저 다듬어드려요"}
            rows={compact ? 1 : 2}
          />
          {/* 밑줄 오버레이: 실제 글자는 투명, 모호한 구간만 빨간 점선 밑줄 */}
          <div className="overlay" ref={overlayRef} aria-hidden>
            <span className="ov-plain">{before}</span>
            {activeRule && (
              <span className="ov-underline">
                {underline}
                <span className="popup">
                  <span className="popup-label">
                    <span className="popup-dot" /> {activeRule.label}
                  </span>
                  <div className="popup-question">{activeRule.question}</div>
                  {activeRule.options.map((opt, i) => (
                    <button
                      key={opt}
                      className={`popup-option ${i === optIdx && !customOpen ? "active" : ""}`}
                      onMouseDown={(e) => { e.preventDefault(); applyOption(opt); }}
                      onMouseEnter={() => setOptIdx(i)}
                    >
                      {opt}
                    </button>
                  ))}
                  {!customOpen ? (
                    <button className="popup-custom-btn" onMouseDown={(e) => { e.preventDefault(); setCustomOpen(true); }}>
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
                        if (e.key === "Enter") { e.preventDefault(); applyOption(customValue || underline); }
                        if (e.key === "Escape") { e.preventDefault(); setCustomOpen(false); }
                      }}
                      placeholder="직접 입력 후 Enter"
                    />
                  )}
                </span>
              </span>
            )}
            <span className="ov-plain">{after}</span>
          </div>
        </div>

        <div className="composer-actions">
          <div className="composer-icons">
            <button className="icon-btn" type="button" title="첨부 (미구현)">
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
              onClick={onExecute}
              title="Enter로도 실행됩니다"
            >
              ↑
            </button>
          </div>
        </div>
      </div>

      {!compact && (
        <div className="hint">
        <b>왜 이렇게 표시되나요?</b> KcELECTRA가 문장의 8요소(Task·Tone 등) 충족 여부를 진단해, 모호한 부분에만 밑줄을 표시해요.
      </div>
      )}

      {gateBlocked && <div className="gate-block">⚠ {gate!.reason}</div>}

      {result && (
        <div className="result">
          <label className="eyebrow">생성 결과</label>
          <pre>{result}</pre>
        </div>
      )}
    </div>
  );
}
