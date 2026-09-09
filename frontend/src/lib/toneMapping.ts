// 직급 기반 존댓말 수위 추천 규칙 (1차 버전)
// 값은 receiver_profile.preferred_tone에 그대로 저장되고,
// ai-service generate_hcx.py의 labels 딕셔너리와 표현을 맞춤 (1단계 참고)

const SENIOR_TITLES = ["이사", "부장", "상무", "전무", "대표"];
const MID_TITLES = ["차장", "과장", "팀장"];
// 그 외(사원, 대리 등)는 편한 존댓말로 취급

export function suggestToneFromJobTitle(jobTitle: string | null | undefined): string | null {
  if (!jobTitle) return null;
  if (SENIOR_TITLES.some((t) => jobTitle.includes(t))) return "격식체";
  if (MID_TITLES.some((t) => jobTitle.includes(t))) return "정중체";
  return "편한존댓말";
}

// 2026-09-08: 프롬프트 안에 사용자가 직접 지정한 톤 표현이 있으면 감지한다.
// suggestToneFromJobTitle()과 같은 값 체계(격식체/정중체/편한존댓말)를 쓴다 -
// 그래야 감지된 값을 기존 저장값과 그대로 비교(다르면 확인 알림)할 수 있다.
// 패턴이 여러 개 매칭되면 배열 순서상 먼저 나온 것을 쓴다(격식 > 정중 > 편한 순).
const EXPLICIT_TONE_PATTERNS: [RegExp, string][] = [
  [/격식\s?있게|격식체로|딱딱하게/, "격식체"],
  [/정중하게|공손하게|예의\s?있게/, "정중체"],
  [/편하게|편한\s?말투로|캐주얼하게|친근하게/, "편한존댓말"],
];

export function detectExplicitTone(prompt: string): string | null {
  for (const [pattern, tone] of EXPLICIT_TONE_PATTERNS) {
    if (pattern.test(prompt)) return tone;
  }
  return null;
}
