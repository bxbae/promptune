"use client";
import { usePathname, useRouter } from "next/navigation";
import AppShell, { NavKey } from "./AppShell";
import { logout } from "@/lib/auth";

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

// 로그인 화면(/) - 사이드바 X
// 나머지 화면 - 사이드바(AppShell) O
// 이 레이아웃은 고정 (수정 시 레이아웃 대규모 수정 필요)
export default function ShellSwitch({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  if (pathname === "/") return <>{children}</>;

  const topSegment = "/" + (pathname.split("/")[1] ?? "");
  // 채팅 스레드는 "채팅"으로 별도 매핑
  const active: NavKey =
    pathname === "/chat"
      ? "newChat"
      : pathname.startsWith("/chat/")
        ? "chat"
        : PATH_TO_KEY[topSegment] ?? "newChat";

  // 파일관리/히스토리/대시보드는 표·카드가 많아 채팅보다 넓은 폭이 필요해서 .page-wide 적용
  const WIDE_PAGES = ["/files", "/history", "/dashboard"];
  const isWide = WIDE_PAGES.some((p) => pathname === p || pathname.startsWith(p + "/"));

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
      <div className={`page ${isWide ? "page-wide" : ""}`}>{children}</div>
    </AppShell>
  );
}