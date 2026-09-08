"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppShell, { NavKey } from "./AppShell";
import { logout, getToken } from "@/lib/auth";
import { getConsentStatus } from "@/api/consents";

// URL ↔ 사이드바 탭 매핑. 새 페이지가 생기면 이 두 곳에 추가
// "새 채팅"(newChat)과 "채팅"(chat, 목록)은 서로 다른 화면이라 경로도 분리함.
const PATH_TO_KEY: Record<string, NavKey> = {
  "/chat": "newChat",
  "/chats": "chat",
  "/files": "files",
  "/history": "history",
  "/dashboard": "dashboard",
  "/settings": "settings",
}
const KEY_TO_PATH: Record<NavKey, string> = {
  newChat: "/chat",
  chat: "/chats",
  files: "/files",
  history: "/history",
  dashboard: "/dashboard",
  settings: "/settings",
}

// 로그인 화면 + 동의 관련 흐름 - 사이드바(AppShell) X, 인증/동의 체크도 스킵
const NO_SHELL_PATHS = ["/", "/oauth/callback", "/consent"];

export default function ShellSwitch({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const bypassShell = NO_SHELL_PATHS.includes(pathname);
  // 인증 확인 → 동의 확인이 끝나기 전까지는 true (보호된 화면을 잠깐이라도 보여주지 않기 위함)
  const [checking, setChecking] = useState(!bypassShell);

  useEffect(() => {
    if (bypassShell) return;
    let cancelled = false;
    setChecking(true);

    // 1) 로그인 여부 - 토큰 자체가 없으면 동의 조회(API)까지 갈 필요 없이 바로 로그인 화면으로
    if (!getToken()) {
      router.replace("/");
      return;
    }

    // 2) 동의 여부
    getConsentStatus()
      .then((allowed) => {
        if (cancelled) return;
        if (!allowed) router.replace("/consent");
        else setChecking(false);
      })
      .catch((err: Error & { authError?: string }) => {
        if (cancelled) return;
        // 2026-09-08: 토큰 만료(401)를 미동의 상태와 혼동해 /consent로
        // 보내던 문제 수정 - 만료면 재로그인이 필요하므로 로그인 화면으로.
        if (err.authError === "token_expired") {
          // 2026-09-08(추가): 토큰을 지우지 않고 리다이렉트만 하면, "/"의
          // getToken() 체크가 만료된 토큰도 "로그인됨"으로 오판해 앞으로
          // 보내고, 그 화면에서 다시 만료 감지 → "/" 되돌림이 반복되며
          // 무한 리다이렉트 루프에 빠진다(실제 재현 확인됨). 반드시
          // 토큰을 지운 뒤에 보내야 루프가 끊긴다.
          logout();
          router.replace("/");
        } else {
          router.replace("/consent");
        }
      });
    return () => { cancelled = true; };
  }, [pathname, bypassShell, router]);

  if (bypassShell) return <>{children}</>;
  if (checking) return null; // 인증/동의 확인 전에는 아무것도 렌더링하지 않음

  const topSegment = "/" + (pathname.split("/")[1] ?? "");
  // 채팅 스레드는 "채팅"으로 별도 매핑
  const active: NavKey =
    pathname === "/chat"
      ? "newChat"
      : pathname.startsWith("/chat/")
        ? "chat"
        : PATH_TO_KEY[topSegment] ?? "newChat";

  // 파일관리/히스토리/대시보드/설정 - 표·카드가 많아 최소 폭(733px)이 필요한 페이지들.
  // 이 페이지들은 좌우 padding 없이, position(가로 중앙)만으로 배치하는 .page-fixed를 사용.
  const FIXED_WIDTH_PAGES = ["/files", "/history", "/dashboard", "/settings"];
  const isFixedWidth = FIXED_WIDTH_PAGES.some((p) => pathname === p || pathname.startsWith(p + "/"));

  return (
    <AppShell
      active={active}
      onNavigate={(key) => router.push(KEY_TO_PATH[key])}
      onNewChat={() => router.push("/chat")}
      onLogout={() => {
        logout();
        router.push("/");
      }}
    >
      <div className={isFixedWidth ? "page-fixed" : "page"}>{children}</div>
    </AppShell>
  );
}