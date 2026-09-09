import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownBoxProps {
  content: string;
}

export default function MarkdownBox({ content }: MarkdownBoxProps) {
  return (
    // 박스 테두리·배경과 문단/리스트 간격은 globals.css의 .markdown-box / .markdown-content에서 관리
    // (이 프로젝트엔 Tailwind가 설치돼 있지 않아 기존 prose/max-w-3xl 등 클래스는 효과가 없었음)
    <div className="markdown-box">
      <article className="markdown-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content}
        </ReactMarkdown>
      </article>
    </div>
  );
}