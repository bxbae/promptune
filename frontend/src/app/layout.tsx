import "./globals.css";
export const metadata = { title: "PrompTune (mock)", description: "프롬프트 개선 코파일럿" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}
