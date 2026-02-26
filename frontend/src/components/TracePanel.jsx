import React from 'react'
import { Card, CardBody, Chip, Divider, ScrollShadow } from '@heroui/react'
import { Activity, TrendingUp, ClipboardList, BarChart3, CheckCircle2, Database } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const TOOL_META = {
  query_deals_board:       { label: 'Query Deals',       Icon: TrendingUp,   color: 'primary' },
  query_work_orders_board: { label: 'Query Work Orders', Icon: ClipboardList, color: 'warning' },
  cross_board_analysis:    { label: 'Cross Analysis',    Icon: BarChart3,    color: 'secondary' },
}

function TraceCard({ trace }) {
  const meta    = TOOL_META[trace.name] ?? { label: trace.name, Icon: Database, color: 'default' }
  const { Icon, label, color } = meta

  const iconBg = {
    primary:   trace.resolved ? 'bg-emerald-500/15' : 'bg-cyan-500/15',
    warning:   trace.resolved ? 'bg-emerald-500/15' : 'bg-orange-500/15',
    secondary: trace.resolved ? 'bg-emerald-500/15' : 'bg-violet-500/15',
    default:   trace.resolved ? 'bg-emerald-500/15' : 'bg-slate-500/15',
  }[color]

  const iconColor = {
    primary:   trace.resolved ? 'text-emerald-400' : 'text-cyan-400',
    warning:   trace.resolved ? 'text-emerald-400' : 'text-orange-400',
    secondary: trace.resolved ? 'text-emerald-400' : 'text-violet-400',
    default:   trace.resolved ? 'text-emerald-400' : 'text-slate-400',
  }[color]

  const argEntries = Object.entries(trace.args ?? {})

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      <Card
        className="bg-white/[0.03] border border-white/[0.06] hover:border-white/[0.1] transition-colors"
        shadow="none"
      >
        <CardBody className="p-3">
          <div className="flex items-start gap-2">
            <div className={`w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5 ${iconBg}`}>
              <Icon size={12} className={iconColor} />
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 mb-1.5">
                <span className="text-xs font-medium text-slate-200 truncate">{label}</span>
                {trace.resolved ? (
                  <CheckCircle2 size={11} className="text-emerald-400 flex-shrink-0" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse flex-shrink-0" />
                )}
              </div>

              {/* Args */}
              {argEntries.length > 0 && (
                <div className="space-y-0.5 mb-1.5">
                  {argEntries.map(([k, v]) => (
                    <p key={k} className="text-[10px] leading-tight">
                      <span className="text-cyan-600/80">{k}:</span>{' '}
                      <span className="text-slate-500">
                        {typeof v === 'string'
                          ? `"${v.slice(0, 28)}${v.length > 28 ? '…' : ''}"`
                          : JSON.stringify(v)}
                      </span>
                    </p>
                  ))}
                </div>
              )}

              {/* Result badge */}
              {trace.resolved && trace.itemCount != null && (
                <Chip
                  size="sm"
                  variant="flat"
                  color="success"
                  className="h-[18px] text-[10px] px-1.5"
                >
                  {trace.itemCount} records returned
                </Chip>
              )}
            </div>
          </div>
        </CardBody>
      </Card>
    </motion.div>
  )
}

export default function TracePanel({ traces }) {
  return (
    <aside className="w-72 flex-shrink-0 flex flex-col h-full border-l border-white/[0.07] bg-white/[0.02]">

      {/* Header */}
      <div className="px-4 py-4 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-cyan-400" />
          <h2 className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest">
            Agent Activity
          </h2>
          {traces.length > 0 && (
            <span className="ml-auto text-[10px] bg-cyan-500/15 text-cyan-400 px-1.5 py-0.5 rounded-full">
              {traces.length}
            </span>
          )}
        </div>
      </div>

      <Divider className="opacity-[0.12]" />

      <ScrollShadow hideScrollBar className="flex-1 overflow-y-auto p-3">
        {traces.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-12 text-center">
            <Activity size={28} className="text-slate-700 mb-3" />
            <p className="text-xs text-slate-600">No activity yet</p>
            <p className="text-[10px] text-slate-700 mt-1">Tool calls appear here in real-time</p>
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence initial={false}>
              {traces.map(trace => (
                <TraceCard key={trace.id} trace={trace} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </ScrollShadow>
    </aside>
  )
}
