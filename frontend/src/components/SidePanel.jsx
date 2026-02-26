import React from 'react'
import { Button, Card, CardBody, Divider, ScrollShadow } from '@heroui/react'
import {
  Zap,
  TrendingUp,
  ClipboardList,
  RefreshCw,
  BarChart3,
  Clock,
  Users,
  Globe,
} from 'lucide-react'

const BOARDS = [
  { name: 'Deals Pipeline',  count: 346, color: 'primary', Icon: TrendingUp  },
  { name: 'Work Orders',     count: 177, color: 'warning', Icon: ClipboardList },
]

const STARTERS = [
  { Icon: TrendingUp,  text: 'How is our pipeline trending this quarter?'            },
  { Icon: Globe,       text: 'Which sector has the highest total deal value?'         },
  { Icon: Clock,       text: 'Show all in-progress work orders and blockers.'         },
  { Icon: BarChart3,   text: 'Compare expected pipeline value against billed amount.' },
  { Icon: Users,       text: 'Which deal owners have the most open opportunities?'    },
  { Icon: Zap,         text: 'Give me a Powerline sector health snapshot.'            },
]

export default function SidePanel({ onSend, onClear, streaming }) {
  return (
    <aside className="w-64 flex-shrink-0 flex flex-col h-full border-r border-white/[0.07] bg-white/[0.02]">

      {/* Brand header */}
      <div className="px-4 py-4 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-700 flex items-center justify-center shadow-lg shadow-cyan-900/40">
            <Zap size={15} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white leading-tight">Skylark BI Agent</h1>
            <p className="text-[10px] text-slate-500 leading-tight">Monday.com Intelligence</p>
          </div>
        </div>
      </div>

      <Divider className="opacity-[0.12]" />

      <ScrollShadow hideScrollBar className="flex-1 overflow-y-auto p-3 space-y-4">

        {/* Connected boards */}
        <div>
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2 px-1">
            Connected Boards
          </p>
          <div className="space-y-1.5">
            {BOARDS.map(({ name, count, color, Icon }) => (
              <Card
                key={name}
                className="bg-white/[0.035] border border-white/[0.06] hover:border-white/[0.1] transition-colors"
                shadow="none"
              >
                <CardBody className="p-2.5">
                  <div className="flex items-center gap-2">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                      color === 'primary' ? 'bg-cyan-500/15' : 'bg-orange-500/15'
                    }`}>
                      <Icon
                        size={13}
                        className={color === 'primary' ? 'text-cyan-400' : 'text-orange-400'}
                      />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-slate-200 truncate">{name}</p>
                      <div className="flex items-center gap-1 mt-0.5">
                        <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${
                          color === 'primary' ? 'bg-cyan-400' : 'bg-orange-400'
                        }`} />
                        <p className="text-[10px] text-slate-500">{count} records · Live</p>
                      </div>
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        </div>

        <Divider className="opacity-[0.08]" />

        {/* Suggested questions */}
        <div>
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2 px-1">
            Suggested Questions
          </p>
          <div className="space-y-0.5">
            {STARTERS.map(({ Icon, text }) => (
              <button
                key={text}
                onClick={() => !streaming && onSend(text)}
                disabled={streaming}
                className="w-full text-left px-2.5 py-2 rounded-lg flex items-start gap-2
                           text-xs text-slate-400 hover:text-slate-100 hover:bg-white/[0.05]
                           transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Icon size={11} className="text-cyan-500 flex-shrink-0 mt-0.5" />
                <span className="leading-snug">{text}</span>
              </button>
            ))}
          </div>
        </div>

      </ScrollShadow>

      <Divider className="opacity-[0.12]" />

      {/* New conversation */}
      <div className="p-3 flex-shrink-0">
        <Button
          size="sm"
          variant="flat"
          color="default"
          className="w-full text-slate-400 hover:text-white bg-white/[0.04]"
          startContent={<RefreshCw size={12} />}
          onPress={onClear}
        >
          New Conversation
        </Button>
      </div>
    </aside>
  )
}
