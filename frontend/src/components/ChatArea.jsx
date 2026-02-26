import React, { useRef, useEffect } from 'react'
import { Button, ScrollShadow } from '@heroui/react'
import {
  Send,
  TrendingUp,
  BarChart3,
  Clock,
  Users,
  Globe,
  Zap,
} from 'lucide-react'
import MessageCard from './MessageCard'

// Short chip labels + the full query sent on click
const SUGGESTIONS = [
  { Icon: TrendingUp, label: 'Pipeline trends',     query: 'How is our pipeline trending this quarter?'              },
  { Icon: Globe,      label: 'Top sectors',          query: 'Which sector has the highest total deal value?'          },
  { Icon: Clock,      label: 'Work order blockers',  query: 'Show all in-progress work orders and blockers.'          },
  { Icon: BarChart3,  label: 'Pipeline vs billed',   query: 'Compare expected pipeline value against billed amount.'  },
  { Icon: Users,      label: 'Top deal owners',      query: 'Which deal owners have the most open opportunities?'     },
  { Icon: Zap,        label: 'Powerline snapshot',   query: 'Give me a Powerline sector health snapshot.'             },
]

function InputBox({ inputRef, value, onChange, onKeyDown, onSend, streaming, placeholder }) {
  // Auto-resize textarea height; reset when value cleared externally
  useEffect(() => {
    if (!value && inputRef?.current) {
      inputRef.current.style.height = 'auto'
    }
  }, [value])

  const handleChange = (e) => {
    onChange(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
  }

  return (
    <div className="flex items-end gap-2">
      <textarea
        ref={inputRef}
        value={value}
        onChange={handleChange}
        onKeyDown={onKeyDown}
        placeholder={placeholder ?? 'Ask anything about your data…'}
        disabled={streaming}
        rows={1}
        className="flex-1 bg-white/[0.05] border border-white/[0.12] rounded-xl
                   px-4 py-3 text-sm text-slate-200 placeholder:text-slate-600
                   resize-none overflow-hidden leading-relaxed
                   focus:outline-none focus:border-cyan-500/60
                   hover:border-white/[0.2] transition-all duration-150
                   disabled:opacity-50 disabled:cursor-not-allowed"
        style={{ minHeight: '44px' }}
      />
      <Button
        isIconOnly
        color="primary"
        size="lg"
        isLoading={streaming}
        isDisabled={!value.trim() || streaming}
        onPress={() => onSend(value)}
        className="flex-shrink-0 bg-cyan-600 hover:bg-cyan-500 min-w-[44px] h-[44px] rounded-xl"
      >
        {!streaming && <Send size={16} />}
      </Button>
    </div>
  )
}

export default function ChatArea({ messages, input, setInput, onSend, streaming }) {
  const bottomRef   = useRef(null)
  const textareaRef = useRef(null)
  const isEmpty     = messages.length === 0

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        textareaRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend(input)
    }
  }

  // ── Welcome / empty state ─────────────────────────────────────────────
  if (isEmpty) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center h-full px-4 min-w-0">
        <div className="w-full max-w-2xl">

          {/* Greeting */}
          <div className="mb-8 text-center select-none">
            <h2 className="text-2xl font-bold text-white mb-1">
              What can I help you with?
            </h2>
            <p className="text-sm text-slate-500">
              Ask anything about your Monday.com pipeline, deals, or work orders.
            </p>
          </div>

          {/* Main input — centered, ChatGPT style */}
          <InputBox
            inputRef={textareaRef}
            value={input}
            onChange={setInput}
            onKeyDown={handleKeyDown}
            onSend={onSend}
            streaming={streaming}
            placeholder="Ask about your pipeline, work orders, or deals…"
          />

          {/* Suggestion chips */}
          <div className="mt-4 flex flex-wrap gap-2 justify-center">
            {SUGGESTIONS.map(({ Icon, label, query }) => (
              <button
                key={label}
                onClick={() => !streaming && onSend(query)}
                disabled={streaming}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full
                           border border-white/[0.1] bg-white/[0.04]
                           text-xs text-slate-400
                           hover:bg-white/[0.09] hover:border-cyan-500/40 hover:text-slate-200
                           transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Icon size={11} className="text-cyan-500 flex-shrink-0" />
                {label}
              </button>
            ))}
          </div>

          <p className="text-[10px] text-slate-700 mt-4 text-center">
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>
    )
  }

  // ── Active chat state ─────────────────────────────────────────────────
  return (
    <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">

      <ScrollShadow hideScrollBar className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
          {messages.map(msg => (
            <MessageCard key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      </ScrollShadow>

      {/* Bottom input bar */}
      <div className="flex-shrink-0 border-t border-white/[0.07] bg-white/[0.02] px-4 py-3">
        <div className="max-w-3xl mx-auto">
          <InputBox
            inputRef={textareaRef}
            value={input}
            onChange={setInput}
            onKeyDown={handleKeyDown}
            onSend={onSend}
            streaming={streaming}
          />
          <p className="text-[10px] text-slate-700 mt-1.5 text-center">
            Enter to send · Shift+Enter for new line · Ctrl+K to focus
          </p>
        </div>
      </div>
    </div>
  )
}
