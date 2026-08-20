"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getElementCoverage,
  getApplyRate,
  getWeeklyActivity,
  ElementCoverage,
  ApplyRate,
  WeeklyActivity,
} from "@/api/dashboard";
import { listReceiverProfiles, ReceiverProfile } from "@/api/receiverProfiles";
import { getPreference, UserPreference } from "@/api/userPreferences";

// 최근 7일 배열, 오래된 순
function last7Days(): string[] {
  const days: string[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }
  return days;
}

const WEEKDAY_KO = ["일", "월", "화", "수", "목", "금", "토"];

function weekdayLabel(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return WEEKDAY_KO[d.getDay()];
}

// 온보딩 value -> 한글 라벨
const PREF_LABEL: Record<string, string> = {
  fast: "빠르게", accurate: "정확하게",
  brief: "간결하게", detailed: "자세하게",
  keep: "최대한 유지", improve: "적극적으로 보완",
};

// TODO: (mock) KPI 값 계산 엔드포인트 추가되면 상수 지우고 실제 API 응답으로 교체.
const MOCK_TOP_KPIS = [
  { label: "출력 형식 누락", value: "5", unit: "건 / 총 7건" },
  { label: "마감일 직접 수정", value: "4", unit: "회" },
  { label: "정중한 말투 적용률", value: "82", unit: "%" },
  { label: "결과 만족도", value: "84", unit: "%" },
];

// TODO: (mock) "추천 적용률"을 항목별로 나누어서 보여주는 API 필요.
// 지금 real data로 있는 건 전체 합산(getApplyRate)뿐이라, 항목별 분해는 mock으로 채움.
const MOCK_APPLY_RATE_BREAKDOWN = [
  { label: "마감일", pct: 86 },
  { label: "말투", pct: 91 },
  { label: "형식", pct: 67 },
  { label: "예시", pct: 13 },
];

// TODO: (mock) task_type별 분포 집계 API 없음. 저장은 있음. 집계하는 백엔드 필요.
// 색상은 카테고리 구분용 (스토리보드 15p 범례 스타일)
const MOCK_TASK_TYPE_DIST = [
  { label: "email", pct: 32, color: "#55806A" },
  { label: "report", pct: 24, color: "#7FA391" },
  { label: "notice", pct: 18, color: "#B7AFB2" },
  { label: "report_internal", pct: 12, color: "#E64B3C" },
  { label: "application", pct: 8, color: "#F2A99A" },
  { label: "support", pct: 4, color: "#D8D3D0" },
  { label: "notice_internal", pct: 2, color: "#EFEBE9" },
];

// 대시보드 페이지
export default function DashboardPage() {
  const [coverage, setCoverage] = useState<ElementCoverage[]>([]);
  const [applyRate, setApplyRate] = useState<ApplyRate | null>(null);
  const [weekly, setWeekly] = useState<WeeklyActivity>({});
  const [receivers, setReceivers] = useState<ReceiverProfile[]>([]);
  const [preference, setPreference] = useState<UserPreference | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      getElementCoverage(),
      getApplyRate(),
      getWeeklyActivity(),
      listReceiverProfiles(),
      getPreference(),
    ])
      .then(([c, a, w, r, p]) => {
        setCoverage(c);
        setApplyRate(a);
        setWeekly(w);
        setReceivers(r);
        setPreference(p);
      })
      .catch((e) => setError(e.message || "대시보드 데이터를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: "20px 0", color: "var(--muted)" }}>불러오는 중...</div>;
  if (error) return <div style={{ padding: "20px 0", color: "var(--block)" }}>{error}</div>;

  const days = last7Days();
  const weeklyValues = days.map((d) => weekly[d] ?? 0);
  const weeklyMax = Math.max(1, ...weeklyValues);
  const weeklyTotal = weeklyValues.reduce((a, b) => a + b, 0);

  const topReceivers = [...receivers]
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
    .slice(0, 3);

  return (
    <div>
      <h1>대시보드</h1>
      {/* 현재 개인화 설정 */}
      <div className="dash-pref-bar">
        <span className="dash-pref-label">현재 개인화 설정</span>
        {preference ? (
          <>
            <span className="dash-pref-pill">{PREF_LABEL[preference.speed] ?? preference.speed}</span>
            <span className="dash-pref-pill">{PREF_LABEL[preference.detail] ?? preference.detail}</span>
            <span className="dash-pref-pill">{PREF_LABEL[preference.preserve] ?? preference.preserve}</span>
          </>
        ) : (
          <span className="dash-pref-pill">설정 안 함</span>
        )}
        <Link href="/history/personalization" className="dash-more-link" style={{ marginLeft: "auto" }}>
          히스토리 &gt; 개인화 설정에서 수정 →
        </Link>
      </div>

      {/* 상단 KPI 4개 (목업) */}
      <div className="dash-kpi-row">
        {MOCK_TOP_KPIS.map((k) => (
          <div className="dash-kpi-card" key={k.label}>
            <div className="dash-kpi-label">{k.label}<span>(mock)</span></div>
            <div className="dash-kpi-value">{k.value} <span className="dash-kpi-unit">{k.unit}</span></div>
          </div>
        ))}
      </div>

      {/* 3열: 요소 포함률 | 수신자별 스타일 | 추천 적용률 */}
      <div className="dash-grid-3">
        {/* 요소 포함률 */}
        <div className="dash-panel">
          <div className="dash-section-title">요소 포함률</div>
          {coverage.length === 0 ? (
            <div className="dash-empty">아직 쌓인 데이터가 없어요.</div>
          ) : (
            <div className="dash-coverage-list">
              {coverage.map((c) => {
                const pct = Math.round(c.coverageRate * 100);
                const good = c.coverageRate >= 0.5;
                return (
                  <div className="dash-coverage-row" key={c.element}>
                    <span className="dash-coverage-label">{c.element}</span>
                    <div className="dash-coverage-bar-track">
                      <div className={`dash-coverage-bar-fill ${good ? "good" : "bad"}`} style={{ width: `${pct}%` }} />
                    </div>
                    <span className={`dash-coverage-pct ${good ? "good" : "bad"}`}>{pct}%</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 수신자별 스타일 */}
        <div className="dash-panel">
          <div className="dash-section-title-row">
            <div className="dash-section-title">수신자별 스타일</div>
          </div>
          <div className="dash-panel-sub">읽기 전용 · 수정은 히스토리에서</div>
          {topReceivers.length === 0 ? (
            <div className="dash-empty">아직 학습된 수신자가 없어요.</div>
          ) : (
            <div className="dash-receiver-list-vertical">
              {topReceivers.map((r) => (
                <div className="dash-receiver-row" key={r.id}>
                  <div>
                    <div className="dash-receiver-name">{r.receiverName}</div>
                    <div className="dash-receiver-relationship">{r.relationship || "-"}</div>
                  </div>
                  <div className="dash-receiver-rate">
                    적용률 {r.applyRate != null ? `${Math.round(r.applyRate * 100)}%` : "-"}
                  </div>
                </div>
              ))}
            </div>
          )}
          <Link href="/history/styles" className="dash-more-link">더보기 →</Link>
        </div>

        {/* 추천 적용률 */}
        <div className="dash-panel">
          <div className="dash-section-title">추천 적용률</div>
          {/* TODO(목업): 항목별 분해 API 없음 - MOCK_APPLY_RATE_BREAKDOWN 참고 */}
          <div className="dash-mock-note">
            ※ 항목별 분해는 예시입니다. 전체 적용률(실제):{" "}
            {applyRate ? `${Math.round(applyRate.applyRate * 100)}%` : "-"}
          </div>
          <div className="dash-coverage-list">
            {MOCK_APPLY_RATE_BREAKDOWN.map((m) => {
              const good = m.pct >= 50;
              return (
                <div className="dash-coverage-row" key={m.label}>
                <span className="dash-coverage-label">{m.label}</span>
                <div className="dash-coverage-bar-track">
                  <div className={`dash-coverage-bar-fill ${good ? "good" : "bad"}`} style={{ width: `${m.pct}%` }} />
                </div>
                <span className={`dash-coverage-pct good ${good ? "good" : "bad"}`}>{m.pct}%</span>
              </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 2열: 업무유형 분포 | 주간 활동 추이 */}
      <div className="dash-grid-2">
        <div className="dash-panel">
          <div className="dash-section-title">업무유형 분포</div>
          {/* TODO(목업): task_type 집계 API 없음 - MOCK_TASK_TYPE_DIST 참고 */}
          <div className="dash-mock-note">※ 예시 데이터입니다. 실제 집계 API는 아직 없어요.</div>
          <div className="dash-tasktype-grid">
            {MOCK_TASK_TYPE_DIST.map((t) => (
              <div className="dash-tasktype-item" key={t.label}>
                <span className="dash-tasktype-dot" style={{ background: t.color }} />
                <span className="dash-tasktype-label">{t.label}</span>
                <span className="dash-tasktype-pct">{t.pct}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="dash-panel">
          <div className="dash-section-title-row">
            <div className="dash-section-title">주간 활동 추이</div>
            <span className="dash-panel-sub">이번 주 총 {weeklyTotal}건</span>
          </div>
          <div className="dash-weekly-chart">
            {days.map((d, i) => (
              <div className="dash-weekly-col" key={d}>
                <div className="dash-weekly-bar-track">
                  <div
                    className="dash-weekly-bar-fill"
                    style={{ height: `${(weeklyValues[i] / weeklyMax) * 100}%` }}
                    title={`${d}: ${weeklyValues[i]}건`}
                  />
                </div>
                <span className="dash-weekly-count">{weeklyValues[i]}</span>
                <span className="dash-weekly-day">{weekdayLabel(d)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
