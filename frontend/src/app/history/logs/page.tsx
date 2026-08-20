"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listActivityLogs, ActivityLogEntry, ActivityType } from "@/api/activityLogs";

type FilterKey = "전체" | ActivityType;
const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "전체", label: "전체" },
  { key: "applied", label: "적용" },
  { key: "rejected", label: "거절" },
  { key: "edited", label: "직접수정" },
];

const TYPE_LABEL: Record<ActivityType, string> = {
  applied: "적용",
  rejected: "거절",
  edited: "직접수정",
};

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function LogsPage() {
  const router = useRouter();
  const [filter, setFilter] = useState<FilterKey>("전체");
  const [logs, setLogs] = useState<ActivityLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    listActivityLogs(filter === "전체" ? undefined : filter)
      .then(setLogs)
      .catch((e) => setError(e.message || "활동 로그를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, [filter]);

  function handleRowClick(entry: ActivityLogEntry) {
    if (entry.chatSessionId == null) return; // 대화가 삭제됐거나 연결 정보가 없는 경우
    router.push(`/chat/${entry.chatSessionId}`);
  }

  return (
    <div>
      <p style={{ color: "var(--muted)", marginTop: 0, marginBottom: 16 }}>
        적용·거절·직접수정 기록을 필터로 걸러볼 수 있어요.
      </p>

      <div className="activity-filter-row">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={`activity-filter-chip ${filter === f.key ? "active" : ""}`}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <div style={{ padding: "20px 0", color: "var(--muted)" }}>불러오는 중...</div>}
      {!loading && error && <div style={{ padding: "20px 0", color: "var(--block)" }}>{error}</div>}

      {/* TODO: 목업데이터 지우고 이거 되살리기 */}
      {/* {!loading && !error && logs.length === 0 && (
        <div style={{ padding: "40px 0", textAlign: "center", color: "var(--muted)" }}>
          아직 기록이 없어요.
        </div>
      )} */}

      {!loading && !error && logs.length > 0 && (
        <div className="activity-table">
          {logs.map((entry, i) => (
            <div
              key={`${entry.occurredAt}-${i}`}
              className={`activity-row ${entry.chatSessionId != null ? "clickable" : ""}`}
              onClick={() => handleRowClick(entry)}
            >
              <span className="activity-time">{formatDateTime(entry.occurredAt)}</span>
              <span className="activity-label">{entry.label}</span>
              <span className={`activity-badge ${entry.type}`}>{TYPE_LABEL[entry.type]}</span>
            </div>
          ))}
        </div>
      )}

      {/* ==================== TODO(목업 미리보기): 확인 끝나면 이 블록 전체 삭제 ====================
          실제 데이터 유무와 무관하게 항상 렌더링되는 독립 섹션. 위쪽 real 데이터 로직과
          전혀 얽혀있지 않아서, 이 블록만 통째로 지우면 목업 제거 끝. */}
      <div className="activity-mock-preview">
        <div className="activity-mock-preview-title">(mock)</div>
        <div className="activity-table">
          {MOCK_ACTIVITY_LOGS.filter((l) => filter === "전체" || l.type === filter).map((entry, i) => (
            <div key={`mock-${i}`} className="activity-row">
              <span className="activity-time">{formatDateTime(entry.occurredAt)}</span>
              <span className="activity-label">{entry.label}</span>
              <span className={`activity-badge ${entry.type}`}>{TYPE_LABEL[entry.type]}</span>
            </div>
          ))}
        </div>
      </div>
      {/* ==================== TODO(목업 미리보기) 끝 ==================== */}
    </div>
  );
}

// TODO(목업): 위 미리보기 섹션 전용 데이터. 섹션 삭제 시 이것도 같이 삭제.
const MOCK_ACTIVITY_LOGS: ActivityLogEntry[] = [
  { type: "applied", label: "김대리에게 보고서 제출 요청", chatSessionId: null, occurredAt: "2026-08-10T09:12:00" },
  { type: "applied", label: "팀 공지 초안 작성", chatSessionId: null, occurredAt: "2026-08-10T08:40:00" },
  { type: "rejected", label: "외부 협력사 견적 문의 메일", chatSessionId: null, occurredAt: "2026-08-09T17:03:00" },
  { type: "edited", label: "박팀장 주간 보고 요약", chatSessionId: null, occurredAt: "2026-08-09T14:21:00" },
  { type: "applied", label: "신규 거래처 A 첫 인사 메일", chatSessionId: null, occurredAt: "2026-08-08T11:55:00" },
  { type: "rejected", label: "사내 정책 변경 안내문", chatSessionId: null, occurredAt: "2026-08-08T10:02:00" },
];
