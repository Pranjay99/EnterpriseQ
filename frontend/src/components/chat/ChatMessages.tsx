'use client'

import { useRef, useEffect } from 'react'
import { Bot, User, Database, FileText, BarChart2, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Message } from '@/types'
import { ChartRenderer } from './ChartRenderer'

interface Props {
  messages: Message[]
  isLoading: boolean
  multiDocIds: number[]
  catalogDocId: number | null
}

export function ChatMessages({ messages, isLoading, multiDocIds, catalogDocId }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8 overflow-y-auto">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
          <Bot className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Enterprise Q</h2>
        <p className="text-muted-foreground text-sm max-w-md">
          Upload a data file or PDF, select a query mode, and start asking questions.
          {multiDocIds.length > 0 && ` Querying ${multiDocIds.length} documents.`}
          {catalogDocId && ` Using catalog document #${catalogDocId}.`}
        </p>
        <div className="grid grid-cols-2 gap-3 mt-6 max-w-sm w-full">
          {[
            'What are the top 10 records by revenue?',
            'Summarize this document',
            'What is 15% of 47800?',
            'Compare trends over time',
          ].map((q) => (
            <div
              key={q}
              className="p-3 rounded-lg border border-border text-xs text-muted-foreground bg-card hover:border-primary/30 hover:text-foreground cursor-pointer transition-colors"
            >
              {q}
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={cn('flex gap-3', msg.role === 'user' ? 'flex-row-reverse' : 'flex-row')}
        >
          <div
            className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
              msg.role === 'user' ? 'bg-primary' : 'bg-secondary'
            )}
          >
            {msg.role === 'user' ? (
              <User className="w-4 h-4" />
            ) : (
              <Bot className="w-4 h-4 text-primary" />
            )}
          </div>

          <div
            className={cn(
              'max-w-[75%] space-y-2',
              msg.role === 'user' ? 'items-end' : 'items-start'
            )}
          >
            <div
              className={cn(
                'px-4 py-3 rounded-2xl text-sm leading-relaxed',
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground rounded-tr-sm'
                  : 'bg-secondary text-foreground rounded-tl-sm'
              )}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>

            {/* SQL Query */}
            {msg.sqlQuery && (
              <details className="w-full">
                <summary className="flex items-center gap-1 text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                  <Database className="w-3 h-3" /> SQL Query
                </summary>
                <pre className="mt-1 p-3 rounded-lg bg-black/50 text-green-400 text-xs overflow-x-auto">
                  {msg.sqlQuery}
                </pre>
              </details>
            )}

            {/* Sources */}
            {msg.sources && msg.sources.length > 0 && (
              <details className="w-full">
                <summary className="flex items-center gap-1 text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                  <FileText className="w-3 h-3" /> Sources ({msg.sources.length})
                </summary>
                <ul className="mt-1 space-y-1">
                  {msg.sources.map((s, i) => (
                    <li
                      key={i}
                      className="text-xs text-muted-foreground bg-secondary px-2 py-1 rounded"
                    >
                      {s}
                    </li>
                  ))}
                </ul>
              </details>
            )}

            {/* Chart */}
            {msg.chartJson && (
              <div className="w-full rounded-lg overflow-hidden border border-border">
                <div className="flex items-center gap-1 px-3 py-2 border-b border-border bg-secondary/50">
                  <BarChart2 className="w-3 h-3 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">Chart</span>
                </div>
                <ChartRenderer chartJson={msg.chartJson} />
              </div>
            )}
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="flex gap-3">
          <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
            <Bot className="w-4 h-4 text-primary" />
          </div>
          <div className="bg-secondary px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
            <span className="text-sm text-muted-foreground">Thinking...</span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
