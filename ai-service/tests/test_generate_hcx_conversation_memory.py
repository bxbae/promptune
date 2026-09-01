import unittest

from app.schemas.models import ConversationMessage, GenerateRequest
from app.services.conversation_memory import (
    build_recall_evidence,
    classify_conversation_context,
    select_relevant_history,
)
from app.services.generate_hcx import (
    _build_recent_user_evidence,
    _build_generation_user_prompt,
)


class ConversationMemoryTest(unittest.TestCase):

    def build_request(self):
        return GenerateRequest(
            prompt="내 프로젝트 명이 뭐라고?",
            task_type="support",
            documents=[],
            web_results=[],
            user_context={},
            preference={},
            history=[
                ConversationMessage(
                    role="user",
                    content="내 이름은 차승연이고 프로젝트는 nested 플랫폼이야 기억해둬",
                ),
                ConversationMessage(
                    role="assistant",
                    content="내 프로젝트 이름은 My Projects입니다.",
                ),
            ],
        )

    def test_recent_user_fact_is_preserved(self):
        req = self.build_request()

        evidence = _build_recent_user_evidence(req)

        self.assertIn("nested 플랫폼", evidence)
        self.assertNotIn("My Projects", evidence)

    def test_recent_user_fact_is_anchored_in_final_prompt(self):
        req = self.build_request()

        prompt = _build_generation_user_prompt(req)

        self.assertIn("nested 플랫폼", prompt)
        self.assertIn("내 프로젝트 명이 뭐라고?", prompt)
        self.assertNotIn("My Projects", prompt)

    def test_p0_1_memory_recall_keeps_original_fact_in_history(self):
        """
        회귀 고정 (P0-1):
        select_relevant_history()가 memory_recall 모드에서
        []를 반환해 1턴 사용자 발화가 history에서 완전히
        사라지던 실제 실패 사례를 fixture로 고정한다.
        """
        history = [
            ConversationMessage(
                role="user",
                content="내 프로젝트는 프롬포튠이야 기억해둬",
            ),
            ConversationMessage(
                role="assistant",
                content="프롬포튠 프로젝트에 대해 기억하겠습니다.",
            ),
        ]
        prompt = "내 프로젝트가 뭐라고?"

        mode = classify_conversation_context(prompt, history)
        self.assertEqual(mode, "memory_recall")

        selected = select_relevant_history(prompt, history)
        selected_contents = [message.content for message in selected]

        self.assertIn(
            "내 프로젝트는 프롬포튠이야 기억해둬",
            selected_contents,
        )

        evidence = build_recall_evidence(prompt, history)

        self.assertIn(
            "내 프로젝트는 프롬포튠이야 기억해둬",
            evidence,
        )


if __name__ == "__main__":
    unittest.main()
