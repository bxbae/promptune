"use client";
import { useState } from "react";
import { grantConsent } from "@/api/consents";

export default function ConsentPage() {
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleAgree() {
    setError(""); setLoading(true);
    try {
      await grantConsent("save");
      window.location.href = "/";
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <div className="auth" style={{ textAlign: "center" }}>
        <h2 style={{ fontSize: 18 }}>서비스 이용 전 확인이 필요해요</h2>
        <label className="auth-consent" style={{ display: "block", margin: "16px 0" }}>
          <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
          (필수) 개인화 습관 저장에 동의합니다
          <span style={{ display: "block", fontSize: 11, color: "#666", marginTop: 30, marginBottom: -25 }}>
            동의하지 않으면 서비스 이용이 제한됩니다.
          </span>
        </label>
        {error && <div className="auth-error">{error}</div>}
        <button className="auth-submit" onClick={handleAgree} disabled={!checked || loading}>
          {loading ? "처리 중…" : "동의하고 시작하기"}
        </button>
      </div>
    </main>
  );
}