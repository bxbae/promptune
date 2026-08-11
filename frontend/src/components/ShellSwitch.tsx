"use client";
import { usePathname, useRouter } from "next/navigation";
import AppShell, { NavKey } from "./AppShell";
import { logout } from "@/lib/auth";

// URL ↔ 사이드바 탭 매핑. 새 페이지가 생기면 이 두 곳에 추가
const PATH_TO_KEY: Record<string, NavKey> = {
  "/chat": "chat",
  "/documents": "documents",
  "/history": "history",
  "/dashboard": "dashboard",
  "/settings": "settings",
}
const KEY_TO_PATH: Record<NavKey, string> = {
  newChat: "/chat",
  chat: "/chat",
  documents: "/documents",
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
  const active = PATH_TO_KEY[topSegment] ?? "chat";

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
      <div className="page">{children}</div>
    </AppShell>
  );
}