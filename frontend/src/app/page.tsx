"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import PromptEditor from "@/components/PromptEditor";
import AuthForm from "@/components/AuthForm";
import AppShell, { NavKey } from "@/components/AppShell";
import { getToken, logout } from "@/lib/auth";

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // 토큰 있으면 로그인 상태로 (목업: 토큰 존재만 확인)
    // TODO(예진): 실제 동작 시 getToken()으로 토큰 확인 후, 백엔드 /api/me 호출해 사용자 이름 받아오기
    // 예진: 개발을 위해 토큰 확인 없이 바로 로그인 상태로 설정
    // if (getToken()) setUser("사용자");   // 실제 동작 시 이 코드 주석 해제
    setUser("사용자");   // 실제 동작 시 이 코드 주석처리
    setReady(true);
  }, []);

  // 로그인되면: 온보딩 안 했으면 /onboarding, 했으면 /chat으로
  useEffect(() => {
    if (!ready || !user) return;
    const onboarded = localStorage.getItem("pt_onboarded") === "1";
    router.replace(onboarded ? "/chat" : "/onboarding");
  }, [ready, user, router]);

  if (!ready || user) return null;


  // 로그인 전: 사이드바 없이 인증 화면만
  return (
    <main className="page">
      <header className="head">
        <h1>PrompTune</h1>
        <p>거친 지시문을 입력하면 부족한 요소를 짚어 되묻고,<br />다듬어진 프롬프트로 결과를 만듭니다.</p>
        {/* TODO: 실제 배포 시 MOCK 문구 제거 */}
        <span className="mock-tag">MOCK — 모델·API는 가짜 응답, 흐름은 실제</span>
      </header>
      <AuthForm onSuccess={setUser} />
    </main>
  );

  /* 
    // 사이드바 네비게이션: 실제 라우트가 있는 탭(설정)은 페이지 이동,
    // 아직 제작 전인 탭은 로컬 placeholder 유지
    function handleNavigate(key: NavKey) {
      if (key === "settings") {
        router.push("/settings");
        return;
      }
      setActive(key);
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
    ) */
}
