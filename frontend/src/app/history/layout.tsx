"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/history/personalization", label: "개인별 맞춤 설정" },
  { href: "/history/styles", label: "수신자별 스타일 관리" },
  { href: "/history/logs", label: "수정이력" },
]

export default function HistoryLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div>
      <h1>히스토리</h1>

      <div style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--line)", margin: "16px 0 24px" }}>
        {TABS.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            style={{
              padding: "8px 14px", fontSize: 14, textDecoration: "none",
              color: pathname === t.href ? "var(--accent)" : "var(--muted)",
              fontWeight: pathname === t.href ? 600 : 400,
              borderBottom: pathname === t.href ? "2px solid var(--accent)" : "2px solid transparent",
            }}
          >
            {t.label}
          </Link>
        ))}
      </div>
      {children}
    </div>
  );
}