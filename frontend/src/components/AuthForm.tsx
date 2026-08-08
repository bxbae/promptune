"use client";
import { useState } from "react";
import { login, signup, saveToken } from "@/lib/auth";

export default function AuthForm({ onSuccess }: { onSuccess: (name: string) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    setError(""); setLoading(true);
    try {
      const res = mode === "login"
        ? await login(email, password)
        : await signup(email, password, name);
      saveToken(res.token);
      onSuccess(res.name || res.email);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
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

      <button className="auth-submit" onClick={handleSubmit} disabled={loading}>
        {loading ? "처리 중…" : mode === "login" ? "로그인" : "가입하기"}
      </button>

      {/* 소셜 로그인 자리 (다음 단계에서 연결) */}
      <div className="auth-divider">또는</div>
      <div className="social-buttons">
        <button className="social google" disabled title="다음 단계에서 연결">Google로 계속</button>
        <button className="social kakao" disabled title="다음 단계에서 연결">카카오로 계속</button>
        <button className="social naver" disabled title="다음 단계에서 연결">네이버로 계속</button>
      </div>
      <p className="auth-note">소셜 로그인은 준비 중입니다 (로컬 로그인 먼저 구현).</p>
    </div>
  );
}
