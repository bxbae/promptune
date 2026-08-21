import unittest

from app.services.diagnose_rules import detect_task_type


class TaskTypeRuleTest(unittest.TestCase):

    def test_meeting_summary_is_report(self):
        text = "\ud68c\uc758 \ub0b4\uc6a9 \uc815\ub9ac\ud574 \uc918"
        self.assertEqual(detect_task_type(text), "report")

    def test_meeting_minutes_is_report(self):
        text = "\ud68c\uc758\ub85d \uc791\uc131\ud574 \uc918"
        self.assertEqual(detect_task_type(text), "report")

    def test_meeting_email_remains_email(self):
        text = "\ud68c\uc758 \uc77c\uc815 \uc548\ub0b4 \uba54\uc77c \uc791\uc131\ud574 \uc918"
        self.assertEqual(detect_task_type(text), "email")

    def test_existing_weekly_report_rule_is_preserved(self):
        text = "\uc8fc\uac04\ubcf4\uace0\uc11c \uc791\uc131\ud574 \uc918"
        self.assertEqual(detect_task_type(text), "report")

    def test_meeting_summary_with_object_particle_is_report(self):
        text = "회의 내용을 정리해줘"
        self.assertEqual(detect_task_type(text), "report")

    def test_meeting_summary_with_object_particle_and_summary_is_report(self):
        text = "회의 내용을 요약해줘"
        self.assertEqual(detect_task_type(text), "report")

    def test_meeting_content_email_remains_email(self):
        text = "회의 내용을 메일로 보내줘"
        self.assertEqual(detect_task_type(text), "email")


if __name__ == "__main__":
    unittest.main()