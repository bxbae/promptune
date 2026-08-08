"use client";
import { useState, useEffect } from "react";
import PromptEditor from "@/components/PromptEditor";
import AuthForm from "@/components/AuthForm";
import { getToken, logout } from "@/lib/auth";

export default function Home() {
  const [user, setUser] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // 토큰 있으면 로그인 상태로 (목업: 토큰 존재만 확인)
    if (getToken()) setUser("사용자");
    setReady(true);
  }, []);

  if (!ready) return null;

  return (
    <main className="page">
      <header className="head">
        <h1>PrompTune</h1>
        <p>거친 지시문을 입력하면 부족한 요소를 짚어 되묻고, 다듬어진 프롬프트로 결과를 만듭니다.</p>
        <span className="mock-tag">MOCK — 모델·API는 가짜 응답, 흐름은 실제</span>
        {user && (
          <button className="logout" onClick={() => { logout(); setUser(null); }}>로그아웃</button>
        )}
      </header>

      {user ? <PromptEditor /> : <AuthForm onSuccess={setUser} />}

      <footer className="foot">단계 0(로그인)·1·2·9·10 · 백엔드 /auth·/analyze·/execute 연동</footer>
    </main>
  );
}
