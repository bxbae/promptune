# Frontend (Next.js)

PrompTune 파이프라인의 **프론트 단계 1,2,9,10** 담당. (예진)
흐름도의 "사용자 입력/조작" 영역.

## 실행

```bash
npm install
npm run dev        # http://localhost:3000

# Docker
docker build -t promptune-frontend . && docker run -p 3000:3000 promptune-frontend
```

> 백엔드(8080)가 떠 있어야 분석·실행이 동작. `docker compose up`으로 전체 실행 권장.

## 구현된 UX 패턴 (흐름도)

| 단계 | 패턴 | 구현 위치 |
|------|------|-----------|
| 1 | 프롬프트 입력 | `PromptEditor` textarea |
| 2 | 입력중단 감지 (0.8초 debounce) | `scheduleAnalyze` + setTimeout |
| 2 | 이전 요청 취소 | AbortController |
| 9 | 인라인 진단 (8요소 상태·밑줄) | `.diagnose`, `.el.target` |
| 9 | Ghost text (흐린 자동완성) | `.ghost-suggest` 오버레이 |
| 10 | Tab 적용 / Esc 무시 / ↑↓ 대안 | `onKeyDown` |
| 11 | Enter 실행 | `onExecute` |

## 구조

```
src/
├── app/
│   ├── page.tsx        # 메인 페이지
│   ├── layout.tsx
│   └── globals.css     # 목업 디자인 토큰
├── components/
│   └── PromptEditor.tsx  # 핵심 — 1,2,9,10 전부
└── lib/
    └── api.ts          # 백엔드 호출 + AbortController
```

## 교체/확장 (예진)

- 지금도 실제 UI로 동작. mock이 아님.
- Ghost text 후보(`GHOST` 상수)는 지금 프론트 하드코딩 → 실제로는 백엔드
  7번(ai /suggest) 응답을 받아 표시하도록 교체.
- 백엔드가 실제 모델로 바뀌면 프론트는 자동으로 실제 데이터를 받음 (수정 불필요).

## 접근성

키보드 포커스 표시, `prefers-reduced-motion` 존중, 모바일 반응형.
