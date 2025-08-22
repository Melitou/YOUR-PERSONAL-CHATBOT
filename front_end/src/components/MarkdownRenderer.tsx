import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
    return (
        <div className={`markdown-content ${className}`}>
            <ReactMarkdown
                components={{
                    // Custom heading components with proper styling
                    h1: ({ children }) => (
                        <h1 className="text-xl font-bold glass-text mb-4 mt-6 first:mt-0 border-b border-white/20 pb-2">
                            {children}
                        </h1>
                    ),
                    h2: ({ children }) => (
                        <h2 className="text-lg font-semibold glass-text mb-3 mt-5 first:mt-0">
                            {children}
                        </h2>
                    ),
                    h3: ({ children }) => (
                        <h3 className="text-base font-medium glass-text mb-2 mt-4 first:mt-0">
                            {children}
                        </h3>
                    ),
                    h4: ({ children }) => (
                        <h4 className="text-sm font-medium glass-text mb-2 mt-3 first:mt-0">
                            {children}
                        </h4>
                    ),
                    // Paragraph styling
                    p: ({ children }) => (
                        <p className="glass-text mb-3 last:mb-0 leading-relaxed">
                            {children}
                        </p>
                    ),
                    // List styling
                    ul: ({ children }) => (
                        <ul className="glass-text mb-3 pl-4 space-y-1">
                            {children}
                        </ul>
                    ),
                    ol: ({ children }) => (
                        <ol className="glass-text mb-3 pl-4 space-y-1 list-decimal">
                            {children}
                        </ol>
                    ),
                    li: ({ children }) => (
                        <li className="glass-text relative">
                            <span className="absolute -left-4 text-white/60">•</span>
                            {children}
                        </li>
                    ),
                    // Emphasis styling
                    strong: ({ children }) => (
                        <strong className="font-semibold text-white">
                            {children}
                        </strong>
                    ),
                    em: ({ children }) => (
                        <em className="italic text-white/90">
                            {children}
                        </em>
                    ),
                    // Code styling
                    code: ({ node, className, children, ...props }: any) => {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match ? match[1] : '';
                        const isInline = !props.inline === false;

                        if (!isInline && language) {
                            // Block code with syntax highlighting
                            return (
                                <div className="my-4 rounded-lg overflow-hidden">
                                    <div className="glass-dark px-3 py-2 text-xs glass-text border-b border-white/10">
                                        {language}
                                    </div>
                                    <SyntaxHighlighter
                                        style={tomorrow as any}
                                        language={language}
                                        PreTag="div"
                                        className="!bg-black/50 !rounded-none !m-0"
                                    >
                                        {String(children).replace(/\n$/, '')}
                                    </SyntaxHighlighter>
                                </div>
                            );
                        } else {
                            // Inline code
                            return (
                                <code
                                    className="glass-dark px-2 py-1 rounded text-sm font-mono text-white/90"
                                >
                                    {children}
                                </code>
                            );
                        }
                    },
                    // Blockquote styling
                    blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-white/30 pl-4 my-4 glass-text italic opacity-90">
                            {children}
                        </blockquote>
                    ),
                    // Table styling
                    table: ({ children }) => (
                        <div className="overflow-x-auto my-4">
                            <table className="min-w-full glass border border-white/20 rounded-lg">
                                {children}
                            </table>
                        </div>
                    ),
                    thead: ({ children }) => (
                        <thead className="glass-dark">
                            {children}
                        </thead>
                    ),
                    tbody: ({ children }) => (
                        <tbody>
                            {children}
                        </tbody>
                    ),
                    tr: ({ children }) => (
                        <tr className="border-b border-white/10">
                            {children}
                        </tr>
                    ),
                    th: ({ children }) => (
                        <th className="px-4 py-2 text-left glass-text font-semibold">
                            {children}
                        </th>
                    ),
                    td: ({ children }) => (
                        <td className="px-4 py-2 glass-text">
                            {children}
                        </td>
                    ),
                    // Horizontal rule
                    hr: () => (
                        <hr className="border-white/20 my-6" />
                    ),
                    // Links (if any)
                    a: ({ children, href }) => (
                        <a
                            href={href}
                            className="text-blue-300 hover:text-blue-200 underline"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            {children}
                        </a>
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

export default MarkdownRenderer;
