import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownBoxProps {
  content: string;
}

export default function MarkdownBox({ content }: MarkdownBoxProps) {
  return (
    // 스타일을 위한 박스 테두리와 배경 지정
    <div className="w-full max-w-3xl p-6 mx-auto my-4 bg-white border border-gray-200 rounded-lg shadow-sm dark:bg-gray-800 dark:border-gray-700">
      
      {/* Tailwind Typography(prose)가 있다면 적용, 없다면 개별 스타일링 필요 */}
      <article className="prose prose-slate dark:prose-invert max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content}
        </ReactMarkdown>
      </article>

    </div>
  );
}