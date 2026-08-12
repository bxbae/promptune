from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TypoRule:
    """
    고신뢰 오탈자 교정 규칙.

    wrong:
        잘못 입력된 표현

    correct:
        교정할 표현

    category:
        keyboard_typo / ending_typo / particle_typo / spelling 등

    priority:
        규칙 간 영역이 겹칠 때 우선순위.
        값이 클수록 먼저 적용한다.
    """

    wrong: str
    correct: str
    category: str
    priority: int


@dataclass(frozen=True, slots=True)
class DetectedTypo:
    """
    실제 입력 문장에서 탐지된 내부 오탈자 객체.

    이 객체는 AI Service 내부에서만 사용한다.
    외부 API 응답은 기존 Typo(span, suggest)를 그대로 유지한다.
    """

    span: str
    suggest: str
    start: int
    end: int
    source: str
    category: str
    priority: int