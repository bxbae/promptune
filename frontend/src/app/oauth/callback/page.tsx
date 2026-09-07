"use client";
import { useEffect, useState } from "react";
import { saveToken } from "@/lib/auth";
import { getConsentStatus } from "@/api/consents";

export default function OAuthCallback() {
  const [msg, setMsg] = useState("로그인 처리 중…");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      saveToken(token);
      setMsg("로그인 성공! 이동합니다…");
      checkConsentAndRedirect();
    } else {
      setMsg("로그인에 실패했습니다. 다시 시도해주세요.");
      setTimeout(() => { window.location.href = "/"; }, 1500);
    }
  }, []);

  async function checkConsentAndRedirect() {
    try {
      const allowed = await getConsentStatus();
      window.location.href = allowed ? "/" : "/consent";
    } catch {
      // 조회 자체가 실패하면 동의 화면으로 보내 안전하게 재확인
      window.location.href = "/consent";
    }
  }

  return (
    <main className="page">
      <div className="auth" style={{ textAlign: "center" }}>
        <h2 style={{ fontSize: 18 }}>{msg}</h2>
      </div>
    </main>
  );
}
