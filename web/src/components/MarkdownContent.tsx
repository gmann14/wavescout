"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface Props {
  content: string;
}

const components: Components = {
  h1: ({ children }) => (
    <h1 className="font-display text-4xl sm:text-5xl font-semibold text-bone border-b border-navy-700 pb-5 mb-8 tracking-tight">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="font-display text-2xl sm:text-[1.75rem] font-semibold text-teal-400 mt-12 mb-4 tracking-tight">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="font-display text-xl font-semibold text-bone mt-9 mb-3 tracking-tight">
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-sm font-semibold uppercase tracking-[0.08em] text-bone-dim mt-7 mb-2">
      {children}
    </h4>
  ),
  p: ({ children }) => (
    <p className="text-bone-dim leading-[1.75] mb-5 max-w-[66ch]">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="text-bone font-semibold">{children}</strong>
  ),
  em: ({ children }) => <em className="text-bone/90">{children}</em>,
  ul: ({ children }) => (
    <ul className="list-disc list-outside ml-5 mb-5 space-y-1.5 text-bone-dim max-w-[66ch]">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside ml-5 mb-5 space-y-1.5 text-bone-dim max-w-[66ch]">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="text-bone-dim leading-[1.75]">{children}</li>
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
    <blockquote className="border-l-2 border-teal-500/70 pl-5 my-6 text-bone/90 font-display text-lg leading-relaxed max-w-[60ch]">
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
    <th className="text-left text-bone font-semibold py-2.5 px-3 font-readout text-xs uppercase tracking-wider">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="text-bone-dim py-2.5 px-3 border-b border-[#1e2d4d]">
      {children}
    </td>
  ),
  hr: () => <hr className="border-navy-700 my-10" />,
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
