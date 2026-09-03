"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PromptEditor, { DirectEdit } from "@/components/PromptEditor";
import { createChatSession } from "@/api/chatSessions";
import { listReceiverProfiles, ReceiverProfile } from "@/api/receiverProfiles";
import type { DocumentItem } from "@/api/documents";

export default function ChatPage() {
  const router = useRouter();
  const [receiverProfiles, setReceiverProfiles] = useState<ReceiverProfile[]>([]);
  const [selectedReceiverProfileId, setSelectedReceiverProfileId] = useState<number | null>(null);

  useEffect(() => {
    listReceiverProfiles()
      .then(setReceiverProfiles)
      .catch(() => {}); // 실패해도 새 채팅 자체는 그대로 진행 (수신자 카드만 안 뜸)
  }, []);

  async function handleFirstSubmit(
    displayText: string,
    directEdits: DirectEdit[],
    attachments: DocumentItem[],
    sendText?: string,
  ) {
    try {
      const session = await createChatSession();
      // /chat/[id] 페이지가 세션 조회 API 없이도 첫 메시지를 바로 실행할 수 있게 잠깐 들고 넘어감
      // displayText: 화면에 보여줄 텍스트, sendText: 실제 AI에 보내는 텍스트(둘이 다를 수 있음 - 파일만 첨부/인용 시)
      // receiverProfileId: 이 화면에서 수신자 스타일 카드로 선택한 값 - /chat/[id]의 첫 실행에도
      // 그대로 반영되게 같이 넘김 (2026-09-03, 예전엔 이 값 자체가 없어서 새 대화 첫 메시지엔
      // 학습된 톤이 전혀 반영이 안 됐음)
      sessionStorage.setItem(
        `chat-first-${session.id}`,
        JSON.stringify({ text: displayText, sendText, directEdits, attachments, receiverProfileId: selectedReceiverProfileId }),
      );
      router.push(`/chat/${session.id}?run=1`);
    } catch (e) {
      console.error("새 대화 시작 실패", e);
      alert("새 대화를 시작하지 못했습니다. 로그인 상태를 확인해주세요.");
    }
  }

  return (
    <PromptEditor
      onSubmit={handleFirstSubmit}
      receiverProfiles={receiverProfiles}
      onReceiverProfileChange={(profile) => setSelectedReceiverProfileId(profile?.id ?? null)}
    />
  );
}