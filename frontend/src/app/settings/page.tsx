"use client";

import { useEffect, useState } from "react";
import { getCurrentUser, logout } from "@/lib/auth";
import MicrosoftProfileView from "./components/MicrosoftProfileView";
import {
  microsoftConnect,
  microsoftDisconnect,
  microsoftEvents,
  microsoftFiles,
  microsoftMessages,
  microsoftProfile,
  microsoftStatus,
} from "@/lib/microsoft";

type MsStatus = {
  connected: boolean;
  microsoftEmail?: string;
  displayName?: string;
};

// TODO(목업 미리보기): 실제 연동 없이 "연결됨" 상태 UI를 확인하기 위한 용도.
// 확인 끝나면 이 상수 + previewMock state/토글 버튼만 지우면 됨 (아래 로직과는 완전히 분리돼있음).
const MOCK_CONNECTED_STATUS: MsStatus = {
  connected: true,
  microsoftEmail: "tester@company.com",
  displayName: "Tester",
};

export default function SettingsPage() {
  const user = getCurrentUser();

  const [msStatus, setMsStatus] = useState<MsStatus>({ connected: false });
  const [msLoading, setMsLoading] = useState(true);
  const [msCallback, setMsCallback] = useState<string | null>(null);
  const [msResult, setMsResult] = useState<unknown>(null);
  const [msError, setMsError] = useState("");
  const [previewMock, setPreviewMock] = useState(false); // TODO(목업 미리보기)

  async function loadMsStatus() {
    try {
      setMsStatus(await microsoftStatus());
    } catch {
      setMsError("Microsoft 연결 상태를 불러오지 못했습니다.");
    } finally {
      setMsLoading(false);
    }
  }

  useEffect(() => {
    setMsCallback(new URLSearchParams(window.location.search).get("microsoft"));
    void loadMsStatus();
  }, []);

  async function handleMsConnect() {
    try {
      const data = await microsoftConnect();
      window.location.href = data.url;
    } catch {
      setMsError("Microsoft 계정 연결을 시작하지 못했습니다.");
    }
  }

  async function handleMsDisconnect() {
    // TODO : 목업, 추후 삭제
    if (previewMock) { alert("목업 미리보기 상태입니다. 실제 연동이 아니에요."); return; }
    // 여기까지
    if (!confirm("Microsoft 계정 연결을 해제할까요?")) return;
    try {
      await microsoftDisconnect();
      setMsResult(null);
      await loadMsStatus();
    } catch {
      setMsError("Microsoft 연결 해제에 실패했습니다.");
    }
  }

  async function runMsQuery(fn: () => Promise<unknown>) {
    // TODO : 목업, 추후 삭제
    if (previewMock) { alert("목업 미리보기 상태입니다. 실제 연동이 아니에요."); return; }
    // 여기까지
    try {
      setMsError("");
      setMsResult(await fn());
    } catch (e) {
      setMsError(e instanceof Error ? e.message : "조회에 실패했습니다.");
    }
  }

  function handleLogout() {
    if (!confirm("로그아웃할까요?")) return;
    logout();
    window.location.href = "/";
  }

  // TODO(목업 미리보기): 실제 연동/조회 대신 mock 상태를 보여주는 동안은 진짜 API를 안 건드림
  const displayStatus = previewMock ? MOCK_CONNECTED_STATUS : msStatus;

  return (
    <div>
      <h1>설정</h1>
      <p style={{ color: "var(--muted)", marginTop: 4, marginBottom: 24 }}>
        계정과 연동 상태를 관리해요.
      </p>

      <div className="settings-list">
        {/* 계정 정보 */}
        <div className="settings-card">
          <div className="settings-card-header">
            <span className="settings-card-title">계정 정보</span>
            <button className="settings-btn" onClick={handleLogout}>로그아웃</button>
          </div>
          <div className="settings-account-row">
            <div className="settings-avatar">{(user?.name || user?.email || "?")[0].toUpperCase()}</div>
            <div>
              <div className="settings-account-name">{user?.name || "이름 없음"}</div>
              <div className="settings-account-email">{user?.email}</div>
            </div>
          </div>
        </div>

        {/* Microsoft 업무 계정 */}
        {!msLoading && (
          <div className="settings-card">
             {/* TODO(목업 미리보기): 확인 끝나면 이 토글 버튼 통째로 삭제 */}
            <button
              className="settings-mock-toggle"
              onClick={() => setPreviewMock((v) => !v)}
            >
              {previewMock ? "목업 미리보기 끄기" : "연결됨 상태 미리보기 (목업)"}
            </button>

            {displayStatus.connected ? (
              <>
                <div className="settings-card-header">
                  <span className="settings-card-title">Microsoft 업무 계정</span>
                  <span className="settings-badge-connected">
                    연결됨{previewMock && " (목업)"}
                  </span>
                </div>
                <p className="settings-card-desc">
                  {displayStatus.microsoftEmail || displayStatus.displayName || "Microsoft 계정"}
                </p>
            {/* {msStatus.connected ? (
              <>
                <div className="settings-card-header">
                  <span className="settings-card-title">Microsoft 업무 계정</span>
                  <span className="settings-badge-connected">연결됨</span>
                </div>
                <p className="settings-card-desc">
                  {msStatus.microsoftEmail || msStatus.displayName || "Microsoft 계정"}
                </p> */}

                <div className="settings-ms-actions">
                  <button className="settings-ms-action-btn" onClick={() => runMsQuery(microsoftProfile)}>프로필</button>
                  <button className="settings-ms-action-btn" onClick={() => runMsQuery(microsoftEvents)}>캘린더</button>
                  <button className="settings-ms-action-btn" onClick={() => runMsQuery(microsoftFiles)}>OneDrive</button>
                  <button className="settings-ms-action-btn" onClick={() => runMsQuery(microsoftMessages)}>메일</button>
                </div>

                <button className="settings-btn-danger" onClick={handleMsDisconnect}>연결 해제</button>

                {msResult !== null && typeof msResult === "object" && "displayName" in msResult ? (
                  <MicrosoftProfileView data={msResult} />
                ) : msResult !== null ? (
                  <pre className="settings-ms-result">{JSON.stringify(msResult, null, 2)}</pre>
                ) : null}
          </>
        ) : (
              <div className="settings-ms-empty">
                <div className="settings-ms-empty-icon">
                  <img src="/icons/microsoft.png" alt="" />
                </div>
                <p className="settings-ms-empty-title">Microsoft 업무 계정</p>
                <p className="settings-ms-empty-desc">
                  연결하면 캘린더·OneDrive·메일 정보를<br />프롬프트 개인화에 활용할 수 있어요.
                </p>
                <button className="settings-btn-primary" onClick={handleMsConnect}>Microsoft 계정 연결</button>
              </div>
            )}

            {msCallback === "connected" && <p className="settings-saved-msg">Microsoft 계정 연결 완료</p>}
            {msCallback === "error" && <p style={{ color: "var(--block)", fontSize: 13, marginTop: 8 }}>Microsoft 계정 연결 실패</p>}
            {msError && <p style={{ color: "var(--block)", fontSize: 13, marginTop: 8 }}>{msError}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
