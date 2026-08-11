"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

type QKey = "speed" | "detail" | "respect";
const QUESTIONS: { key: QKey; title: string; options: { value: string; label: string; desc: string }[] }[] = [
  {
    key: "speed",
    title: "1. 속도 vs 정확도",
    options: [
      { value: "fast", label: "빠르게", desc: "짧게 다듬고 바로 다음 작업으로" },
      { value: "accurate", label: "정확하게", desc: "시간이 걸려도 꼼꼼하게 검토" },
    ],
  },
  {
    key: "detail",
    title: "2. 설명 분량",
    options: [
      { value: "brief", label: "간결하게", desc: "핵심만 짧게, 바로 적용" },
      { value: "detailed", label: "자세하게", desc: "추천 근거까지 알고 싶어요" },
    ],
  },
  {
    key: "respect",
    title: "3. 원문 존중도",
    options: [
      { value: "keep", label: "최대한 유지", desc: "빠진 조건만 채우고 말투는 그대로" },
      { value: "imporve", label: "적극적으로 보완", desc: "더 매끄러운 쪽으로 바꿔도 OK" }, 
    ],
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [answers, setAnswers] = useState<Partial<Record<QKey, string>>>({});

  function finish() {
    localStorage.setItem("pt_onboarding", "1");
    localStorage.setItem("pt_onboarding_answers", JSON.stringify(answers));
    router.replace("/chat");
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto" }}>
      <h1>결과물을 어떤 형식으로 받고 싶으세요?</h1>
      <p style={{ color: "var(--muted)" }}>
        3가지만 골라주시면, 다음부턴 물어보지 않고 학습한 내용을 바탕으로 추천해드려요.
      </p>

      {/* 질문-선택지 */}
      {QUESTIONS.map((q) => (
        <div key={q.key} style={{ marginTop: 24 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>
            {q.title}
          </div>

          <div style={{ display: "flex", gap: 12 }}>
            {q.options.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setAnswers((a) => ({ ...a, [q.key]: opt.value }))}
                style={{
                  flex: 1, textAlign: "left", padding: 14, borderRadius: 10,
                  border: `1px solid ${answers[q.key] === opt.value ? "var(--accent)" : "var(--line)"}`,
                  background: answers[q.key] === opt.value ? "var(--accent-tint)" : "var(--panel)",
                  cursor: "pointer", fontFamily: "inherit",
                }}
              >
                <div style={{ fontWeight: 600 }}>{opt.label}</div>
                <div style={{ fontSize: 13, color: "var(--muted)" }}>{opt.desc}</div>
              </button>
            ))}
          </div>
        </div>
      ))}

      {/* 하단 버튼 */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 32}}>
        <span>3개 중 {Object.keys(answers).length}개 선택함</span>

        <div style={{ display: "flex", gap: 12 }}>
          <button
            onClick={finish}
            style={{ background: "none", border: "none", color: "var(--muted)", cursor: "pointer" }}
          >
            나중에 설정할게요
          </button>
          <button
            onClick={finish}
            style={{ padding: "10px 20px", borderRadius: 8, border: "none", background: "var(--accent)", color: "#fff", cursor: "pointer" }}
          >
            시작하기
          </button>
        </div>
      </div>
    </div>
  );
}