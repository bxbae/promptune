import "./globals.css";
import ShellSwitch from "@/components/ShellSwitch";

// TODO: 실제 배포 시 (mock) 제거
export const metadata = { title: "PrompTune (mock)", description: "프롬프트 개선 코파일럿" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <ShellSwitch>{children}</ShellSwitch>
      </body>
    </html>
  );
}
