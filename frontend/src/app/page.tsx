import PromptEditor from "@/components/PromptEditor";
export default function Home() {
  return (
    <main className="page">
      <header className="head">
        <h1>PrompTune</h1>
        <p>거친 지시문을 입력하면 부족한 요소를 짚어 되묻고, 다듬어진 프롬프트로 결과를 만듭니다.</p>
        <span className="mock-tag">MOCK — 모델·API는 가짜 응답, 흐름은 실제</span>
      </header>
      <PromptEditor />
      <footer className="foot">단계 1·2·9·10 (프론트) · 백엔드 /analyze·/execute 연동</footer>
    </main>
  );
}
