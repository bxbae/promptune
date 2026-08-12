"use client";
import { useEffect, useRef, useState } from "react";

export type NavKey = "newChat" | "chat" | "files" | "history" | "dashboard" | "settings";

const NAV_ITEMS: { key: NavKey; label: string, icon: string }[] = [
  { key: "files", label: "파일관리", icon: "files" },
  { key: "history", label: "히스토리", icon: "history" },
  { key: "dashboard", label: "대시보드", icon: "dashboard" },
  { key: "settings", label: "설정", icon: "settings" },
]

interface AppShellProps {
  active: NavKey;
  onNavigate: (key: NavKey) => void;
  onNewChat?: () => void;
  userEmail?: string;
  onLogout?: () => void;
  // onSwitchAccount?: () => void;
  children: React.ReactNode;
}

export default function AppShell({
  active,
  onNavigate,
  onNewChat,
  // userEmail은 로그인 후 사용자 이메일로 표시되도록 추후 구현 예정
  userEmail = "demo@promptune.dev",
  onLogout,
  // onSwitchAccount,
  children,
}: AppShellProps) {
  const [dark, setDark] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  // const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);

  // 저장된 다크모드 · 사이드바 접힘 상태 복원
  useEffect(() => {
    if (localStorage.getItem("pt_theme") === "dark") setDark(true);
    if (localStorage.getItem("pt_sidebar_collapsed") === "1") setCollapsed(true);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    localStorage.setItem("pt_theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    localStorage.setItem("pt_sidebar_collapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  // 계정 메뉴 바깥 클릭 시 닫기
  /* useEffect(() => {
    if (!accountMenuOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (accountMenuRef.current && !accountMenuRef.current.contains(e.target as Node)) {
        setAccountMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [accountMenuOpen]); */


  // 프로필 사진 대신 이메일 첫 글자와 이름 표시 (임시)
  const initial = userEmail.slice(0, 1).toUpperCase();
  const name = userEmail.split("@")[0].toUpperCase();

  return (
    <div className="shell">
      {/* 사이드바 */}
      <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
        {/* 로고: 클릭 시 홈으로 이동 + 사이드바 토글*/}
        <div className="sidebar-header">
          <button type="button" className="sidebar-logo"
            onClick={() => {
              onNavigate("newChat");
              onNewChat?.();
            }}
            style={{ width: "fit-content", background: "none", border: "none", cursor: "pointer" }}>
            <span className="logo-icon">P</span>
            <span>PrompTune</span>
          </button>
          <button
            className="collapse-btn"
            onClick={() => setCollapsed((c) => !c)}
            title={collapsed ? "펼치기" : "접기"}
          >
            <img src="/icons/collapse.png" alt="" />
          </button>
        </div>

        {/* 새 채팅 버튼 */}
        <button
          className={`new-chat-btn ${active === "newChat" ? "active" : ""}`}
          onClick={() => {
            onNavigate("newChat");
            onNewChat?.();
          }}
        >
          <span className="label-icon"><img src="/icons/plus-muted.png" alt="" /></span>
          <span className="label-icon-active"><img src="/icons/plus-active.png" alt="" /></span>
          <span className="label">새 채팅</span>
        </button>

        {/* 네비게이션 메뉴 */}
        <nav className="nav-list">
          <button
            className={`nav-item ${active === "chat" ? "active" : ""}`}
            onClick={() => onNavigate("chat")}
          >
            <span className="label-icon"><img src="/icons/chats-muted.png" alt="" /></span>
            <span className="label-icon-active"><img src="/icons/chats-active.png" alt="" /></span>
            <span className="label">채팅</span>
          </button>

          <div className="sidebar-spacer" style={{ borderTop: "1px solid var(--line)" }} />

          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`nav-item ${active === item.key ? "active" : ""}`}
              onClick={() => onNavigate(item.key)}
              title={item.label}
            >
              <span className="label-icon">
                <img src={`/icons/${item.icon}-muted.png`} alt="" />
              </span>
              <span className="label-icon-active">
                <img src={`/icons/${item.icon}-active.png`} alt="" />
              </span>
              <span className="label">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-spacer" />

        {/* 하단: 다크모드 토글, 계정 정보, 로그아웃 */}
        <div className="sidebar-bottom">
          {/* 다크모드 토글 */}
          <div className="theme-row">
            <span className="label">다크 모드</span>
            <label className="switch">
              <input
                type="checkbox"
                checked={dark}
                onChange={(e) => setDark(e.target.checked)}
              />
              <span className="switch-track" />
              <span className="switch-thumb" />
            </label>
          </div>

          {/* 사용자 정보 */}
          <div className="user-row-wrap" ref={accountMenuRef}>
            <button
              type="button"
              className="user-row"
              // onClick={() => setAccountMenuOpen((v) => !v)}
              aria-haspopup="menu"
              // aria-expanded={accountMenuOpen}
              title={userEmail}
            >
              <span className="avatar">{initial}</span>
              <span className="user-meta label">
                <span className="user-name">{name}</span>
                <span className="user-email">{userEmail}</span>
              </span>
            </button>

            {/*{accountMenuOpen && (
              <div className="account-menu" role="menu">
                <button
                  type="button"
                  className="account-menu-item"
                  role="menuitem"
                  onClick={() => {
                    setAccountMenuOpen(false);
                    onSwitchAccount?.();
                  }}
                >
                  계정 전환
                </button>
              </div>
            )}*/}
          </div>

          {/* 로그아웃 버튼 */}
          <button className="logout-link label" onClick={onLogout}>
            <span className="label-icon"><img src="/icons/logout.png" /></span>
            로그아웃
          </button>
        </div>

      </aside>

      {/* 메인 컨텐츠 */}
      <main className="content">{children}</main>
    </div>
  )
}