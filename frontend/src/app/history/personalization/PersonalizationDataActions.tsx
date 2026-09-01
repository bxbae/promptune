"use client";
import { useState, type CSSProperties } from "react";
import {
  deleteAllChatHistory,
  exportPersonalization,
  resetPersonalization,
} from "@/api/personalization";
import { listReceiverProfiles, deleteReceiverProfile } from "@/api/receiverProfiles";
import { listDocuments, deleteDocument } from "@/api/documents";
import ConfirmDialog from "@/components/ConfirmDialog";

type PendingAction = "receivers" | "history" | "reset";

const CONFIRM_TEXT: Record<PendingAction, { title: string; message: string; confirmLabel: string }> = {
  receivers: {
    title: "수신자별 학습 데이터 초기화",
    message: "모든 수신자 스타일 프로필을 지우고 새로 학습할까요? 삭제한 데이터는 복구할 수 없습니다.",
    confirmLabel: "초기화",
  },
  history: {
    title: "작업 이력 전체 삭제",
    message: "작업 이력(채팅·프롬프트 기록)과 업로드한 파일을 전부 삭제할까요? 삭제한 데이터는 복구할 수 없습니다.",
    confirmLabel: "삭제",
  },
  reset: {
    title: "전체 데이터 초기화",
    message: "개인화 데이터(설정·수신자 스타일·수정 이력) + 업로드한 파일을 전부 삭제할까요? 삭제한 데이터는 복구할 수 없습니다.",
    confirmLabel: "초기화",
  },
};

// 개인화 데이터(습관 데이터·수신자 프로필) 전체 초기화 / 내보내기 + 작업 이력(채팅 기록+업로드 파일) 전체 삭제.
// - "전체 초기화"·"내보내기"는 백엔드 PersonalizationController가 이미 제공 (선호 설정+수신자 프로필+관련 동의/학습 데이터)
// - "작업 이력 전체 삭제"는 채팅 세션/프롬프트 기록(ChatSessionController) + 업로드 파일(DocumentController)을
//   각각 따로 지워서 합친 것 - 백엔드에 통합 삭제 엔드포인트가 없어서 프론트에서 두 API를 같이 호출함.
export default function PersonalizationDataActions() {
  const [busy, setBusy] = useState<"receivers" | "history" | "export" | "reset" | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  // 파괴적 액션 3개(초기화/삭제/전체초기화)를 공용 모달 하나로 처리 - 누른 버튼 기억
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);

  async function doResetReceivers() {
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

  async function doDeleteHistory() {
    setBusy("history");
    setError("");
    setMessage("");
    try {
      const docs = await listDocuments();
      await Promise.all([deleteAllChatHistory(), ...docs.map((d) => deleteDocument(d.id))]);
      setMessage("작업 이력과 업로드한 파일을 모두 삭제했습니다.");
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

  async function doResetAll() {
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

  const ACTION_RUNNERS: Record<PendingAction, () => Promise<void>> = {
    receivers: doResetReceivers,
    history: doDeleteHistory,
    reset: doResetAll,
  };

  async function handleConfirm() {
    if (!pendingAction) return;
    await ACTION_RUNNERS[pendingAction]();
    setPendingAction(null);
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
          <button onClick={() => setPendingAction("receivers")} disabled={busy !== null} style={buttonStyle()}>
            {busy === "receivers" ? "초기화 중..." : "초기화"}
          </button>
        </div>

        <div className="pref-data-row">
          <div>
            <div className="pref-data-row-title">작업 이력 전체 삭제</div>
            <div className="pref-data-row-desc">채팅·프롬프트 기록과 업로드한 파일을 모두 삭제</div>
          </div>
          <button onClick={() => setPendingAction("history")} disabled={busy !== null} style={buttonStyle()}>
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
          <div className="pref-data-row-title" style={{ color: "var(--block)" }}>전체 개인화 데이터 초기화 <span className="pref-data-row-desc">개인화 데이터(설정·수신자 스타일·수정 이력) + 업로드 파일 전부 삭제</span></div>
        </div>
        <button onClick={() => setPendingAction("reset")} disabled={busy !== null} style={buttonStyle(true)}>
          {busy === "reset" ? "초기화 중..." : "전체 초기화"}
        </button>
      </div>

      <ConfirmDialog
        open={pendingAction !== null}
        title={pendingAction ? CONFIRM_TEXT[pendingAction].title : ""}
        message={pendingAction ? CONFIRM_TEXT[pendingAction].message : ""}
        confirmLabel={pendingAction ? CONFIRM_TEXT[pendingAction].confirmLabel : "확인"}
        danger
        loading={busy !== null}
        onConfirm={handleConfirm}
        onCancel={() => setPendingAction(null)}
      />
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
