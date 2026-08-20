"use client";
import { useState, type CSSProperties } from "react";
import {
  deleteAllChatHistory,
  exportPersonalization,
  resetPersonalization,
} from "@/api/personalization";
import { listReceiverProfiles, deleteReceiverProfile } from "@/api/receiverProfiles";

// 개인화 데이터(습관 데이터·수신자 프로필) 전체 초기화 / 내보내기 + 작업 이력(채팅 기록) 전체 삭제.
// - "전체 초기화"·"내보내기"는 백엔드 PersonalizationController가 이미 제공 (선호 설정+수신자 프로필+관련 동의/학습 데이터)
// - "작업 이력 전체 삭제"는 별도로 채팅 세션/프롬프트 기록만 삭제 (ChatSessionController)
export default function PersonalizationDataActions() {
  const [busy, setBusy] = useState<"receivers" | "history" | "export" | "reset" | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleResetReceivers() {
    if (!confirm("모든 수신자 스타일 프로필을 지우고 새로 학습할까요? 삭제한 데이터는 복구할 수 없습니다.")) return;
    setBusy("receivers");
    setError("");
    setMessage("");
    try {
      const receivers = await listReceiverProfiles();
      await Promise.all(receivers.map((r) => deleteReceiverProfile(r.id)));
      setMessage("수신자별 학습 데이터를 초기화했습니다.");
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

  async function handleResetAll() {
    if (!confirm("설정 + 수신자 스타일 + 수정 이력을 전부 삭제할까요? 삭제한 데이터는 복구할 수 없습니다.")) return;
    setBusy("reset");
    setError("");
    setMessage("");
    try {
      await resetPersonalization();
      setMessage("개인화 데이터를 전체 초기화했습니다.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "초기화에 실패했습니다.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <div className="pref-data-box">
        <div className="pref-data-title">개인 맞춤 데이터 관리</div>

        <div className="pref-data-row">
          <div>
            <div className="pref-data-row-title">수신자별 학습 데이터 초기화</div>
            <div className="pref-data-row-desc">모든 수신자 스타일 프로필을 지우고 새로 학습</div>
          </div>
          <button onClick={handleResetReceivers} disabled={busy !== null} style={buttonStyle()}>
            {busy === "receivers" ? "초기화 중..." : "초기화"}
          </button>
        </div>

        <div className="pref-data-row">
          <div>
            <div className="pref-data-row-title">작업 이력 전체 삭제</div>
            <div className="pref-data-row-desc">채팅·프롬프트 기록을 모두 삭제</div>
          </div>
          <button onClick={handleDeleteHistory} disabled={busy !== null} style={buttonStyle()}>
            {busy === "history" ? "삭제 중..." : "삭제"}
          </button>
        </div>

        <div className="pref-data-row">
          <div>
            <div className="pref-data-row-title">내 데이터 내보내기</div>
            <div className="pref-data-row-desc">쌓인 개인화 데이터를 JSON으로 다운로드</div>
          </div>
        <button onClick={handleExport} disabled={busy !== null} style={buttonStyle()}>
          {busy === "export" ? "내보내는 중..." : "내보내기"}
        </button>
        </div>

        {message && <p style={{ marginTop: 12, fontSize: 13, color: "var(--accent)" }}>{message}</p>}
        {error && <p style={{ marginTop: 12, fontSize: 13, color: "var(--block)" }}>{error}</p>}
      </div>

      {/* 전체 초기화는 파급 범위가 제일 커서 박스 밖으로 분리 */}
      <div className="pref-data-danger-row">
        <div>
          <div className="pref-data-row-title" style={{ color: "var(--block)" }}>전체 개인화 데이터 초기화 <span className="pref-data-row-desc">설정 + 수신자 스타일 + 수정 이력 전부 삭제</span></div>
        </div>
        <button onClick={handleResetAll} disabled={busy !== null} style={buttonStyle(true)}>
          {busy === "reset" ? "초기화 중..." : "전체 초기화"}
        </button>
      </div>
    </>
  );
}

function buttonStyle(danger = false): CSSProperties {
  return {
    padding: "8px 16px",
    borderRadius: 8,
    border: danger ? "none" : "1px solid var(--line)",
    background: danger ? "var(--block)" : "var(--panel)",
    color: danger ? "#fff" : "var(--ink)",
    fontSize: 13,
    fontWeight: danger ? 600 : 400,
    cursor: "pointer",
    fontFamily: "inherit",
    flexShrink: 0,
  };
}
