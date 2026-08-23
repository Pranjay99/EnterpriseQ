'use client'

import { useState, useRef, KeyboardEvent } from 'react'
import { Send, Loader2, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { QueryMode } from '@/types'
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuGroup, DropdownMenuLabel, DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'

const QUERY_MODES: { value: QueryMode; label: string; description: string; icon: string }[] = [
  { value: 'auto', label: 'Auto', description: 'Pick the best agent automatically', icon: '✨' },
  { value: 'sql', label: 'Text-to-SQL', description: 'Query structured data', icon: '🗄️' },
  { value: 'dataframe', label: 'DataFrame Analysis', description: 'Pandas-powered analysis', icon: '📊' },
  { value: 'rag', label: 'Document Q&A', description: 'RAG over documents', icon: '📄' },
  { value: 'general', label: 'Math & Reasoning', description: 'Calculations & logic', icon: '🧮' },
]

interface Props {
  onSend: (message: string) => void
  isLoading: boolean
  disabled: boolean
  queryMode: QueryMode
  onQueryModeChange: (m: QueryMode) => void
}

export function ChatInput({ onSend, isLoading, disabled, queryMode, onQueryModeChange }: Props) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const activeMode = QUERY_MODES.find((m) => m.value === queryMode) ?? QUERY_MODES[0]

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || isLoading || disabled) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`
    }
  }

  return (
    <div className="p-4 border-t border-border bg-card">
      <div className="flex items-end gap-2 bg-secondary rounded-xl px-3 py-3 border border-border focus-within:border-primary/50 transition-colors">
        {/* Agent / mode picker */}
        <DropdownMenu>
          <DropdownMenuTrigger
            title={`Agent: ${activeMode.label} — click to change`}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-base shrink-0 hover:bg-background/60 border border-transparent hover:border-border transition-colors"
          >
            {activeMode.icon}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" side="top" className="w-60">
            <DropdownMenuGroup>
              <DropdownMenuLabel className="text-xs">Choose agent</DropdownMenuLabel>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            {QUERY_MODES.map((m) => (
              <DropdownMenuItem
                key={m.value}
                onClick={() => onQueryModeChange(m.value)}
                className="gap-2.5 cursor-pointer"
              >
                <span className="text-base">{m.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium">{m.label}</p>
                  <p className="text-[10px] text-muted-foreground">{m.description}</p>
                </div>
                {queryMode === m.value && <Check className="w-3.5 h-3.5 text-primary shrink-0" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Ask a question... (Enter to send, Shift+Enter for newline)"
          rows={1}
          className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground resize-none outline-none min-h-[24px] max-h-40 leading-6"
          disabled={isLoading || disabled}
        />
        <button
          onClick={handleSend}
          disabled={!value.trim() || isLoading || disabled}
          className={cn(
            'w-8 h-8 rounded-lg flex items-center justify-center transition-colors shrink-0',
            value.trim() && !isLoading
              ? 'bg-primary text-primary-foreground hover:bg-primary/90'
              : 'bg-muted text-muted-foreground cursor-not-allowed'
          )}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>
      <p className="text-[10px] text-muted-foreground/40 text-center mt-2">
        Agent: {activeMode.label} · Enterprise Q may make mistakes. Verify important information.
      </p>
    </div>
  )
}
