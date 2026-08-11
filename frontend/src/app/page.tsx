"use client";
import { useState, useEffect } from "react";
import PromptEditor from "@/components/PromptEditor";
import AuthForm from "@/components/AuthForm";
import AppShell, { NavKey } from "@/components/AppShell";
import { getToken, logout } from "@/lib/auth";

export default function Home() {
  const [user, setUser] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [active, setActive] = useState<NavKey>("newChat");

  useEffect(() => {
    // 토큰 있으면 로그인 상태로 (목업: 토큰 존재만 확인)
    // 예진: 개발을 위해 토큰 확인 없이 바로 로그인 상태로 설정
    // if (getToken()) setUser("사용자");
    setUser("사용자");   // 실제 동작 시 이 코드 주석처리
    setReady(true);
  }, []);

  if (!ready) return null;


  // 로그인 전: 사이드바 없이 인증 화면만
  if (!user) {
    return (
      <main className="page">
        <header className="head">
          <h1>PrompTune</h1>
          <p>거친 지시문을 입력하면 부족한 요소를 짚어 되묻고, 다듬어진 프롬프트로 결과를 만듭니다.</p>
          <span className="mock-tag">MOCK — 모델·API는 가짜 응답, 흐름은 실제</span>
        </header>
        <AuthForm onSuccess={setUser} />
      </main>
    );
  }

  // 로그인 후: AppShell(사이드바) + 새 채팅 화면
  return (
    <AppShell
      active={active}
      onNavigate={setActive}
      onNewChat={() => setActive("newChat")}
      onLogout={() => {
        logout();
        setUser(null);
      }}
    >
      <div className="page">
        {active === "newChat" && <PromptEditor />}
        {active !== "newChat" && (
          <div style={{padding: "40px 0", color: "var(--muted)"}}>
            "{active}" 화면은 추후 제작 예정
          </div>
        )}
      </div>
    </AppShell>
  )
}
