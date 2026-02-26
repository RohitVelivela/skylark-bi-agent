import React from 'react'
import { Card, CardBody, Spinner } from '@heroui/react'
import { Zap } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function MarkdownContent({ content }) {
  return (
    <div className="md-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Wrap tables for horizontal scroll on small widths
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto">
              <table {...props} />
            </div>
          ),
          // Open links in new tab
          a: ({ node, ...props }) => (
            <a target="_blank" rel="noopener noreferrer" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default function MessageCard({ message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[78%]">
          <div className="bg-cyan-600/20 border border-cyan-500/25 rounded-2xl rounded-tr-sm px-4 py-3">
            <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[92%] w-full">
        <div className="flex items-start gap-2.5">

          {/* Avatar */}
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cyan-600 to-cyan-800 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-md shadow-cyan-900/40">
            <Zap size={13} className="text-white" />
          </div>

          {/* Bubble */}
          <Card
            className="flex-1 bg-white/[0.04] border border-white/[0.07]"
            shadow="none"
          >
            <CardBody className="p-4">
              {message.pending ? (
                <div className="flex items-center gap-2.5">
                  <Spinner size="sm" color="primary" />
                  <span className="text-sm text-slate-500">Analyzing your data…</span>
                </div>
              ) : message.error ? (
                <div className="text-sm text-red-400">
                  <MarkdownContent content={message.content} />
                </div>
              ) : (
                <MarkdownContent content={message.content} />
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
