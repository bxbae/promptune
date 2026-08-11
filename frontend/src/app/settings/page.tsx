"use client";

import { useEffect, useState } from "react";
import {
  microsoftConnect,
  microsoftDisconnect,
  microsoftEvents,
  microsoftFiles,
  microsoftMessages,
  microsoftStatus,
} from "../../lib/microsoft";

type Status = {
  connected: boolean;
  microsoftEmail?: string;
  displayName?: string;
};

export default function SettingsPage() {
  const [status, setStatus] = useState<Status>({ connected: false });
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState("");
  const [callback, setCallback] = useState<string | null>(null);

  async function loadStatus() {
    try {
      setStatus(await microsoftStatus());
    } catch {
      setError("Microsoft 연결 상태를 불러오지 못했습니다.");
    }
  }

  useEffect(() => {
    setCallback(new URLSearchParams(window.location.search).get("microsoft"));
    void loadStatus();
  }, []);

  async function connect() {
    try {
      const data = await microsoftConnect();
      window.location.href = data.url;
    } catch {
      setError("Microsoft 계정 연결을 시작하지 못했습니다.");
    }
  }

  async function disconnect() {
    try {
      await microsoftDisconnect();
      setResult(null);
      await loadStatus();
    } catch {
      setError("Microsoft 연결 해제에 실패했습니다.");
    }
  }

  async function run(fn: () => Promise<unknown>) {
    try {
      setError("");
      setResult(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "조회에 실패했습니다.");
    }
  }

  return (
    <main style={{ maxWidth: 900, margin: "40px auto", padding: 24 }}>
      <h1>설정</h1>

      <section style={{ marginTop: 32, padding: 24, border: "1px solid #ddd" }}>
        <h2>Microsoft 업무 계정</h2>

        {callback === "connected" && <p>Microsoft 계정 연결 완료</p>}
        {callback === "error" && <p>Microsoft 계정 연결 실패</p>}

        {status.connected ? (
          <>
            <p>
              연결 계정: {status.microsoftEmail || status.displayName || "Microsoft 계정"}
            </p>

            <button onClick={disconnect}>연결 해제</button>

            <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
              <button onClick={() => run(microsoftEvents)}>캘린더 조회</button>
              <button onClick={() => run(microsoftFiles)}>OneDrive 조회</button>
              <button onClick={() => run(microsoftMessages)}>메일 조회</button>
            </div>
          </>
        ) : (
          <button onClick={connect}>Microsoft 계정 연결</button>
        )}

        {error && <p>{error}</p>}

        {result !== null && (
          <pre style={{ marginTop: 24, padding: 16, overflow: "auto" }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </section>

      <p style={{ marginTop: 24 }}>
        <a href="/">메인으로 돌아가기</a>
      </p>
    </main>
  );
}
