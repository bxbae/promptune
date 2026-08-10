"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { analyze, execute, AnalyzeResponse } from "@/lib/api";

const EL_KOR: Record<string, string> = {
  TASK: "작업", AUDIENCE: "대상", CONTEXT: "배경", FORMAT: "형식",
  TONE: "어조", LENGTH: "분량", CONSTRAINT: "제약", EXAMPLE: "예시",
};
// 6번에서 추천된 요소 → Ghost text 후보 (mock: 실제론 7번 ai /suggest 호출)
const GHOST: Record<string, string> = {
  AUDIENCE: " 팀장님께", TONE: " 정중하게", FORMAT: " 표로",
  LENGTH: " 300자 이내로", CONTEXT: " 지난 회의 관련해서",
  CONSTRAINT: " 전문용어는 빼고", EXAMPLE: " 지난번 양식처럼", TASK: " 요약해줘",
};

export default function PromptEditor() {
  const [text, setText] = useState("");
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [ghostIdx, setGhostIdx] = useState(0);      // 10번: ↑↓ 대안 인덱스
  const [result, setResult] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 2번: 입력 중단 감지 (0.8초) → 분석. 재입력 시 이전 요청 취소.
  const scheduleAnalyze = useCallback((value: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (abortRef.current) abortRef.current.abort();   // 이전 요청 취소
    if (!value.trim()) { setAnalysis(null); return; }
    timerRef.current = setTimeout(async () => {
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      try {
        setLoading(true);
        const res = await analyze(value, ctrl.signal);
        setAnalysis(res);
        setGhostIdx(0);
      } catch (e: any) {
        if (e.name !== "AbortError") console.error(e);
      } finally {
        setLoading(false);
      }
    }, 800);
  }, []);

  useEffect(() => () => {   // 언마운트 정리
    if (timerRef.current) clearTimeout(timerRef.current);
    if (abortRef.current) abortRef.current.abort();
  }, []);

  // 6번 추천 요소 (Ghost text로 보여줄 것)
  const targets = analysis?.recommend?.targetElements ?? [];
  const ghostEl = targets[ghostIdx % (targets.length || 1)];
  const ghostText = ghostEl ? GHOST[ghostEl] ?? "" : "";

  // 10번: 키보드 조작 (Tab 적용 / Esc 무시 / ↑↓ 대안)
  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (!ghostText) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onExecute(); }
      return;
    }
    if (e.key === "Tab") {                    // 적용
      e.preventDefault();
      const next = text + ghostText;
      setText(next);
      scheduleAnalyze(next);
    } else if (e.key === "Escape") {          // 무시
      setAnalysis((a) => a ? { ...a, recommend: { targetElements: [] } } : a);
    } else if (e.key === "ArrowDown") {       // 대안 다음
      e.preventDefault(); setGhostIdx((i) => i + 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault(); setGhostIdx((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); onExecute();
    }
  }

  async function onExecute() {               // 11번
    if (!text.trim()) return;
    setLoading(true);
    const res = await execute(text);
    setResult(res?.result?.result ?? JSON.stringify(res));
    setLoading(false);
  }

  const missing = analysis?.diagnose?.missing ?? {};
  const gateBlocked = analysis && !analysis.gate.passed;

  return (
    <div className="editor">
      <label className="eyebrow">프롬프트 입력</label>
      <div className="input-wrap">
        <textarea
          value={text}
          onChange={(e) => { setText(e.target.value); scheduleAnalyze(e.target.value); }}
          onKeyDown={onKeyDown}
          placeholder="업무 지시문을 입력하세요. 예: 회의록 정리해줘"
          rows={3}
        />
        {/* 9번: Ghost text (흐린 자동완성) */}
        {ghostText && (
          <div className="ghost" aria-hidden>
            <span className="ghost-typed">{text}</span>
            <span className="ghost-suggest">{ghostText}</span>
          </div>
        )}
      </div>

      <div className="hint">
        {loading ? "분석 중…" :
          ghostText ? <>Tab 적용 · Esc 무시 · ↑↓ 대안 · Enter 실행</> :
          "입력을 멈추면 분석합니다 · Enter 실행"}
      </div>

      {/* 3번 게이트 차단 */}
      {gateBlocked && <div className="gate-block">⚠ {analysis!.gate.reason}</div>}

      {/* 5번 진단 결과 — 8요소 상태 */}
      {analysis?.diagnose && (
        <div className="diagnose">
          <div className="row">
            <span className="tag">업무유형</span>
            <b>{analysis.diagnose.taskType}</b>
            {analysis.diagnose.needsInternalDocs && <span className="badge">내부문서 참조</span>}
          </div>
          <div className="elements">
            {Object.entries(missing).map(([el, v]) => (
              <span key={el} className={`el ${v === 1 ? "miss" : "ok"} ${targets.includes(el) ? "target" : ""}`}>
                {EL_KOR[el]}{v === 1 ? " 보완필요" : " 충분"}
              </span>
            ))}
          </div>
          {analysis.diagnose.typos.length > 0 && (
            <div className="typos">오탈자: {analysis.diagnose.typos.map(t => `${t.span}→${t.suggest}`).join(", ")}</div>
          )}
        </div>
      )}

      {/* 14번 결과 */}
      {result && (
        <div className="result">
          <label className="eyebrow">생성 결과</label>
          <pre>{result}</pre>
        </div>
      )}
    </div>
  );
}
