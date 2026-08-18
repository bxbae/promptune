"use client";
import { useState, type CSSProperties } from "react";
import {
  deleteAllChatHistory,
  exportPersonalization,
  resetPersonalization,
} from "@/api/personalization";

// 개인화 데이터(습관 데이터·수신자 프로필) 전체 초기화 / 내보내기 + 작업 이력(채팅 기록) 전체 삭제.
// - "전체 초기화"·"내보내기"는 백엔드 PersonalizationController가 이미 제공 (선호 설정+수신자 프로필+관련 동의/학습 데이터)
// - "작업 이력 전체 삭제"는 별도로 채팅 세션/프롬프트 기록만 삭제 (ChatSessionController)
export default function PersonalizationDataActions() {
  const [busy, setBusy] = useState<"reset" | "export" | "history" | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleExport() {
    setBusy("export");
    setError("");
    setMessage("");
    try {
      const data = await exportPersonalization();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "promptune-personalization-data.json";
      a.click();
      URL.revokeObjectURL(url);
      setMessage("내보내기가 완료됐습니다.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "내보내기에 실패했습니다.");
    } finally {
      setBusy(null);
    }
  }

  async function handleReset() {
    if (!confirm("습관 데이터(선호 설정)와 수신자 프로필을 모두 삭제할까요? 삭제한 데이터는 복구할 수 없습니다.")) return;
    setBusy("reset");
    setError("");
    setMessage("");
    try {
      await resetPersonalization();
      setMessage("개인화 데이터(습관 데이터·수신자 프로필)를 초기화했습니다.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "초기화에 실패했습니다.");
    } finally {
      setBusy(null);
    }
  }

  async function handleDeleteHistory() {
    if (!confirm("작업 이력(채팅·프롬프트 기록) 전체를 삭제할까요? 삭제한 데이터는 복구할 수 없습니다.")) return;
    setBusy("history");
    setError("");
    setMessage("");
    try {
      await deleteAllChatHistory();
      setMessage("작업 이력을 모두 삭제했습니다.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "작업 이력 삭제에 실패했습니다.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div
      style={{
        marginTop: 32,
        padding: 16,
        border: "1px solid var(--line)",
        background: "var(--panel)",
        borderRadius: 12,
      }}
    >
      <div style={{ fontWeight: 600, fontSize: 14 }}>개인화 데이터 관리</div>
      <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>
        수신자 프로필ㆍ습관 데이터ㆍ작업 이력을 내보내거나, 원하는 항목만 골라 삭제할 수 있습니다.
      </p>

      <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
        <button onClick={handleExport} disabled={busy !== null} style={buttonStyle()}>
          {busy === "export" ? "내보내는 중..." : "내보내기"}
        </button>
        <button onClick={handleReset} disabled={busy !== null} style={buttonStyle()}>
          {busy === "reset" ? "초기화 중..." : "습관 데이터·수신자 프로필 초기화"}
        </button>
        <button onClick={handleDeleteHistory} disabled={busy !== null} style={buttonStyle()}>
          {busy === "history" ? "삭제 중..." : "작업 이력 전체 삭제"}
        </button>
      </div>

      {message && <p style={{ marginTop: 12, fontSize: 13 }}>{message}</p>}
      {error && <p style={{ marginTop: 12, fontSize: 13, color: "var(--block)" }}>{error}</p>}
    </div>
  );
}

function buttonStyle(): CSSProperties {
  return {
    padding: "8px 14px",
    borderRadius: 8,
    border: "1px solid var(--line)",
    background: "var(--bg)",
    color: "var(--ink)",
    fontSize: 13,
    cursor: "pointer",
    fontFamily: "inherit",
  };
}
