'use client'

import { Files, MessagesSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { MultiDocMode } from '@/types'
import { Button } from '@/components/ui/button'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

interface Props {
  docCount: number
  chatWithDocs: boolean
  onToggleChatWithDocs: () => void
  multiDocMode: MultiDocMode
  onMultiDocModeChange: (m: MultiDocMode) => void
}

export function ChatTopBar({
  docCount,
  chatWithDocs,
  onToggleChatWithDocs,
  multiDocMode,
  onMultiDocModeChange,
}: Props) {
  return (
    <div className="h-12 shrink-0 px-4 border-b border-border bg-card flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-sm font-semibold">Chat</span>
        {docCount > 0 && (
          <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-secondary text-muted-foreground">
            <Files className="w-3 h-3" />
            {docCount} document{docCount > 1 ? 's' : ''} selected
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {chatWithDocs && docCount > 1 && (
          <Select
            value={multiDocMode}
            onValueChange={(v) => { if (v !== null) onMultiDocModeChange(v as MultiDocMode) }}
          >
            <SelectTrigger className="h-8 text-xs w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="synthesize">Synthesize</SelectItem>
              <SelectItem value="compare">Compare</SelectItem>
              <SelectItem value="per_doc">Per Document</SelectItem>
            </SelectContent>
          </Select>
        )}
        {docCount > 0 && (
          <Button
            size="sm"
            variant={chatWithDocs ? 'default' : 'outline'}
            onClick={onToggleChatWithDocs}
            className={cn('h-8 gap-1.5 text-xs', chatWithDocs && 'shadow')}
            title={
              chatWithDocs
                ? 'Questions are answered from the selected documents — click to switch back to session data'
                : 'Route your questions to the selected documents'
            }
          >
            <MessagesSquare className="w-3.5 h-3.5" />
            {chatWithDocs ? 'Chatting with documents' : 'Chat with documents'}
          </Button>
        )}
      </div>
    </div>
  )
}
