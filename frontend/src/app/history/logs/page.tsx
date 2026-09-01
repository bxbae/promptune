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
  return `${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours() + 9)}:${pad(d.getMinutes())}`;
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

      {!loading && !error && logs.length === 0 && (
        <div style={{ padding: "40px 0", textAlign: "center", color: "var(--muted)" }}>
          아직 기록이 없어요.
        </div>
      )}

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
    </div>
  );
}
