"use client";
import { useState } from "react";
import { login, signup, saveToken } from "@/lib/auth";
import { grantConsent } from "@/api/consents";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export default function AuthForm({ onSuccess }: { onSuccess: (name: string) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);

  async function handleSubmit() {
    if (mode === "signup" && !consentChecked) return;
    setError(""); setLoading(true);
    try {
      const res = mode === "login"
        ? await login(email, password)
        : await signup(email, password, name);
      saveToken(res.token);
      if (mode === "signup") {
        await grantConsent("save"); // 회원가입 시 자동으로 동의 처리
      }
      onSuccess(res.name || res.email);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // 소셜 로그인: 백엔드 OAuth2 시작 경로로 이동
  function social(provider: "google" | "kakao" | "naver") {
    window.location.href = `${API}/oauth2/authorization/${provider}`;
  }

  return (
    <div className="auth">
      <div className="auth-tabs">
        <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>로그인</button>
        <button className={mode === "signup" ? "active" : ""} onClick={() => setMode("signup")}>회원가입</button>
      </div>

      {mode === "signup" && (
        <input placeholder="이름" value={name} onChange={(e) => setName(e.target.value)} />
      )}
      <input type="email" placeholder="이메일" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" placeholder="비밀번호" value={password}
        onChange={(e) => setPassword(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }} />

      {error && <div className="auth-error">{error}</div>}

      {mode === "signup" && (
        <label className="auth-consent">
          <input type="checkbox" checked={consentChecked} onChange={(e) => setConsentChecked(e.target.checked)} />
          <span>(필수) 개인화 습관 저장에 동의</span>
        </label>
      )}

      <button className="auth-submit" onClick={handleSubmit} disabled={loading || (mode === "signup" &&!consentChecked)}>
        {loading ? "처리 중…" : mode === "login" ? "로그인" : "가입하기"}
      </button>

      <div className="auth-divider">또는</div>
      <div className="social-buttons">
        <button className="social google" onClick={() => social("google")}>Google로 계속</button>
        <button className="social kakao" onClick={() => social("kakao")}>카카오로 계속</button>
        <button className="social naver" onClick={() => social("naver")}>네이버로 계속</button>
      </div>
    </div>
  );
}
