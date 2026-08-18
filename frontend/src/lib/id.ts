// 고유 ID 생성 유틸.
//
// crypto.randomUUID()는 "secure context"(HTTPS 또는 localhost)에서만 동작한다.
// 지금처럼 IP 주소로 http://로 접속하는 환경에서는 secure context가 아니라서
// crypto.randomUUID가 undefined가 되어 "crypto.randomUUID is not a function" 에러가 난다.
// (HTTPS 적용 전까지는 이 fallback이 필요함 — docs/EC2_배포_가이드.md의 "나중에 개선: HTTPS" 참고)
//
// crypto.getRandomValues()는 secure context 여부와 상관없이 항상 사용 가능하므로
// 이를 이용해 직접 UUID v4를 만든다. crypto 객체 자체가 없는 아주 예외적인 경우에는
// Math.random() 기반으로 최종 폴백한다.
export function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    const bytes slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }

  // 최종 폴백 (암호학적으로 안전하진 않지만 화면 표시용 key/id로는 충분)
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
