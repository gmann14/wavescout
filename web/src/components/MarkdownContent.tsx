"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface Props {
  content: string;
}

const components: Components = {
  h1: ({ children }) => (
    <h1 className="text-3xl font-bold text-slate-100 border-b border-slate-700 pb-4 mb-6">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-2xl font-semibold text-teal-400 mt-10 mb-4">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-xl font-semibold text-slate-200 mt-8 mb-3">
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-lg font-medium text-slate-300 mt-6 mb-2">
      {children}
    </h4>
  ),
  p: ({ children }) => (
    <p className="text-slate-400 leading-relaxed mb-4">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="text-slate-200 font-semibold">{children}</strong>
  ),
  em: ({ children }) => <em className="text-slate-300">{children}</em>,
  ul: ({ children }) => (
    <ul className="list-disc list-outside ml-5 mb-4 space-y-1.5 text-slate-400">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside ml-5 mb-4 space-y-1.5 text-slate-400">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="text-slate-400 leading-relaxed">{children}</li>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-teal-400 hover:text-teal-300 underline underline-offset-2"
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-teal-500 pl-4 my-4 text-slate-300 italic">
      {children}
    </blockquote>
  ),
  code: ({ className, children }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      return (
        <code className="block bg-[#162038] rounded-lg p-4 text-sm text-teal-300 overflow-x-auto my-4 border border-[#1e2d4d]">
          {children}
        </code>
      );
    }
    return (
      <code className="bg-[#162038] text-teal-400 px-1.5 py-0.5 rounded text-sm border border-[#1e2d4d]">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <pre className="my-4">{children}</pre>,
  table: ({ children }) => (
    <div className="overflow-x-auto my-6">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="border-b-2 border-teal-500/30">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="text-left text-slate-300 font-semibold py-2.5 px-3">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="text-slate-400 py-2.5 px-3 border-b border-[#1e2d4d]">
      {children}
    </td>
  ),
  hr: () => <hr className="border-slate-700 my-8" />,
};

export default function MarkdownContent({ content }: Props) {
  return (
    <div className="max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
