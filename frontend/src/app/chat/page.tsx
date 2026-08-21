"use client";
import { useRouter } from "next/navigation";
import PromptEditor, { DirectEdit } from "@/components/PromptEditor";
import { createChatSession } from "@/api/chatSessions";

export default function ChatPage() {
  const router = useRouter();

  async function handleFirstSubmit(text: string, directEdits: DirectEdit[]) {
    try {
      const session = await createChatSession();
      // /chat/[id] 페이지가 세션 조회 API 없이도 첫 메시지를 바로 실행할 수 있게 잠깐 들고 넘어감
      // "직접 입력"기록 넘기기 위해 JSON으로 저장
      sessionStorage.setItem(`chat-first-${session.id}`, JSON.stringify({ text, directEdits }));
      router.push(`/chat/${session.id}?run=1`);
    } catch (e) {
      console.error("새 대화 시작 실패", e);
      alert("새 대화를 시작하지 못했습니다. 로그인 상태를 확인해주세요.");
    }
  }

  return <PromptEditor onSubmit={handleFirstSubmit}/>;
}