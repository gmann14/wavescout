"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
}

export default function MarkdownContent({ content }: Props) {
  return (
    <div className="prose prose-invert prose-sm max-w-none
      prose-headings:text-slate-200
      prose-h1:text-2xl prose-h1:font-bold prose-h1:border-b prose-h1:border-navy-700 prose-h1:pb-3
      prose-h2:text-xl prose-h2:text-teal-400 prose-h2:mt-8
      prose-h3:text-base prose-h3:text-slate-300
      prose-p:text-slate-400 prose-p:leading-relaxed
      prose-strong:text-slate-200
      prose-em:text-slate-400
      prose-code:text-teal-400 prose-code:bg-navy-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm
      prose-pre:bg-navy-800 prose-pre:border prose-pre:border-navy-700
      prose-a:text-teal-400 prose-a:no-underline hover:prose-a:underline
      prose-table:text-sm
      prose-th:text-slate-300 prose-th:border-navy-600 prose-th:py-2 prose-th:px-3
      prose-td:text-slate-400 prose-td:border-navy-700 prose-td:py-2 prose-td:px-3
      prose-li:text-slate-400
      prose-ul:text-slate-400
    ">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
