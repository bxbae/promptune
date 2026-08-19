"use client";
import { useEffect, useState } from "react";
import { getPreference, upsertPreference } from "@/api/userPreferences";
import PersonalizationDataActions from "./PersonalizationDataActions";

// TODO: onboarding/page.tsx의 QUESTIONS와 완전히 동일. 공용 상수 파일로 분리 고려
type QKey = "speed" | "detail" | "preserve";
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
    key: "preserve",
    title: "3. 원문 존중도",
    options: [
      { value: "keep", label: "최대한 유지", desc: "빠진 조건만 채우고 말투는 그대로" },
      { value: "improve", label: "적극적 보완", desc: "더 매끄러운 쪽으로 바꿔도 OK" },
    ],
  },
];

export default function PersonalizationPage() {
  const [answers, setAnswers] = useState<Partial<Record<QKey, string>>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getPreference()
      .then((pref) => {
        if (!pref) return;
        setAnswers({
          speed: pref.speed ?? undefined,
          detail: pref.detail ?? undefined,
          preserve: pref.preserve ?? undefined,
        });
      })
      .catch((e) => setError(e.message || "설정을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  async function save() {
    if (saving) return;
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      await upsertPreference({
        speed: answers.speed ?? null,
        detail: answers.detail ?? null,
        preserve: answers.preserve ?? null,
      });
      setSaved(true);
    } catch (e: any) {
      setError(e.message || "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div style={{ padding: "20px 0", color: "var(--muted)" }}>불러오는 중...</div>;
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <p style={{ color: "var(--muted)", marginTop: 0 }}>
        첫 이용 때 고른 3가지 설정이에요. 언제든 다시 바꿀 수 있어요.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 16,
          marginTop: 20,
        }}
      >
        {QUESTIONS.map((q) => (
          <div
            key={q.key}
            style={{
              padding: 16, border: "1px solid var(--line)",
              background: "var(--panel)", borderRadius: 12,
              display: "flex", flexDirection: "column", gap: 10,
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 14 }}>{q.title}</div>

            <div style={{ display: "flex", gap: 8 }}>
              {q.options.map((opt) => {
                const active = answers[q.key] === opt.value;
                return (
                  <button
                    key={opt.value}
                    onClick={() => { setAnswers((a) => ({ ...a, [q.key]: opt.value })); setSaved(false); }}
                    style={{
                      flex: 1, padding: "8px 6px", borderRadius: 8,
                      border: `1px solid ${active ? "var(--accent)" : "var(--line)"}`,
                      background: active ? "var(--accent-tint)" : "var(--bg)",
                      color: active ? "var(--accent)" : "var(--ink)",
                      fontWeight: active ? 600 : 400,
                      fontSize: 13, cursor: "pointer", fontFamily: "inherit",
                      textAlign: "center", whiteSpace: "nowrap",
                    }}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {error && <div style={{ color: "var(--block)", marginTop: 16 }}>{error}</div>}

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 28 }}>
        <button
          onClick={save}
          disabled={saving}
          style={{
            padding: "10px 20px", borderRadius: 8, border: "none",
            background: "var(--accent)", color: "#fff",
            cursor: saving ? "default" : "pointer", opacity: saving ? 0.7 : 1,
          }}
        >
          {saving ? "저장 중..." : "변경사항 저장"}
        </button>
        <span style={{ fontSize: 13, color: "var(--muted)" }}>
          {saved ? "저장했어요. 대시보드·홈 화면에 바로 반영돼요." : "대시보드·홈 화면에 바로 반영돼요"}
        </span>
      </div>

      <PersonalizationDataActions />
    </div>
  )
}