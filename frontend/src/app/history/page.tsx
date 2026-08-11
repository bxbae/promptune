import { redirect } from "next/navigation";

// /history 로 들어오면 첫 번째 탭으로 보냄
export default function HistoryIndexPage() {
  redirect("/history/personalization");
}
