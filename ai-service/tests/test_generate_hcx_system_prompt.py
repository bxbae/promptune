import sys
import types
import unittest

# 2026-08-26: generate_hcx가 모듈 최상단에서 `import torch`와
# `from app.services.hcx_runtime import hcx_lock, load_hcx_runtime`를 하는데,
# 이 테스트는 순수 문자열 조립 함수(_build_system_prompt)만 확인하므로 실제
# 모델 로딩은 필요 없다. test_retrieval_orchestrator.py와 동일한 최소 스텁으로
# 무거운 import 체인을 끊는다 (ai-service Docker 이미지에는 실제 torch/
# transformers가 설치돼 있음 - requirements.txt 참고, 여기선 샌드박스 한정 우회).
#
# 주의: 이 스텁을 module import 시점에 sys.modules에 영구로 남기면(예전 시도),
# 같은 프로세스에서 `python -m unittest discover`로 여러 테스트 파일을 한 번에
# 돌릴 때 알파벳순으로 뒤에 실행되는 다른 파일(예: test_improve_hcx.py)이 진짜
# torch 대신 이 가짜 스텁을 import하게 돼서, 원래는 "torch 없음"으로 깔끔하게
# import 에러가 나야 할 테스트가 스텁의 부족한 기능 때문에 엉뚱하게 실패하는
# 부작용이 확인됨. setUpModule/tearDownModule로 이 파일이 실행되는 동안만
# 스텁을 걸고, 끝나면 반드시 원상복구한다.
_installed_torch_stub = False
_installed_hcx_runtime_stub = False

_build_system_prompt = None
GenerateRequest = None


def setUpModule():
    global _installed_torch_stub, _installed_hcx_runtime_stub
    global _build_system_prompt, GenerateRequest

    if "torch" not in sys.modules:
        import contextlib

        torch_stub = types.ModuleType("torch")
        torch_stub.inference_mode = contextlib.nullcontext

        class _StubTensor:
            pass

        torch_stub.Tensor = _StubTensor
        sys.modules["torch"] = torch_stub
        _installed_torch_stub = True

    if "app.services.hcx_runtime" not in sys.modules:
        hcx_runtime_stub = types.ModuleType("app.services.hcx_runtime")
        hcx_runtime_stub.hcx_lock = lambda timeout=None: None
        hcx_runtime_stub.load_hcx_runtime = lambda: (None, None, None)
        sys.modules["app.services.hcx_runtime"] = hcx_runtime_stub
        _installed_hcx_runtime_stub = True

    from app.schemas.models import GenerateRequest as _GenerateRequest
    from app.services.generate_hcx import _build_system_prompt as _bsp

    GenerateRequest = _GenerateRequest
    _build_system_prompt = _bsp


def tearDownModule():
    # 이 파일이 실제로 설치한 스텁만 제거한다 (이미 다른 곳에서 진짜 torch가
    # 로드돼 있던 경우는 절대 건드리지 않음).
    sys.modules.pop("app.services.generate_hcx", None)

    if _installed_torch_stub:
        sys.modules.pop("torch", None)

    if _installed_hcx_runtime_stub:
        sys.modules.pop("app.services.hcx_runtime", None)


class BuildSystemPromptRelevanceRulesTest(unittest.TestCase):
    """
    2026-08-26: "이강인 축구선수" 질의에서 웹 검색 결과에 실제 관련 기사가
    있었는데도 모델이 그걸 무시하고 오래된 사전 지식(소속팀 "PSG", 존재하지
    않는 "K리그1 데뷔")으로 답한 사례, "침착맨" 질의에서 무관한 정치 기사
    1건을 근거로 답변한 사례가 확인됨. 시스템 프롬프트에 "검색 결과가 질문
    대상과 실제로 관련 있는지 확인" + "시간에 따라 바뀌는 사실은 사전 지식보다
    참고자료를 우선" 규칙이 반드시 포함돼야 한다.
    """

    def _prompt(self, web_results):
        req = GenerateRequest(
            prompt="이강인 축구선수에 대해 알려줘",
            task_type="report",
            documents=[],
            web_results=[],
            user_context={},
            preference={},
            history=[],
        )
        return _build_system_prompt(req, web_results)

    def test_includes_relevance_check_rule(self):
        prompt = self._prompt([])
        self.assertIn("무관한", prompt)
        self.assertIn("질문 대상", prompt)

    def test_includes_prefer_current_reference_over_prior_knowledge_rule(self):
        prompt = self._prompt([])
        self.assertIn("사전 지식", prompt)
        self.assertIn("참고자료를 따르고", prompt)


if __name__ == "__main__":
    unittest.main()
