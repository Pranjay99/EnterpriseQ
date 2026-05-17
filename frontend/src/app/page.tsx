'use client'

import { useState, useCallback, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { ChatSidebar } from '@/components/chat/ChatSidebar'
import { ChatMessages } from '@/components/chat/ChatMessages'
import { ChatInput } from '@/components/chat/ChatInput'
import { sendChat } from '@/lib/api'
import type { Message, QueryMode, MultiDocMode } from '@/types'

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string>('')

  useEffect(() => {
    const stored = sessionStorage.getItem('session_id')
    if (stored) {
      setSessionId(stored)
    } else {
      const id = Math.random().toString(36).substring(2, 10)
      sessionStorage.setItem('session_id', id)
      setSessionId(id)
    }
  }, [])

  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [queryMode, setQueryMode] = useState<QueryMode>('sql')
  const [dataLoaded, setDataLoaded] = useState(false)
  const [docLoaded, setDocLoaded] = useState(false)
  const [catalogDocId, setCatalogDocId] = useState<number | null>(null)
  const [multiDocIds, setMultiDocIds] = useState<number[]>([])
  const [multiDocMode, setMultiDocMode] = useState<MultiDocMode>('synthesize')
  const [uploadedFile, setUploadedFile] = useState<{
    name: string
    rows?: number
    columns?: number
    chunks?: number
  } | null>(null)
  // Read URL params for catalog/multi-doc selections
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const docId = params.get('doc_id')
    const docIds = params.get('doc_ids')
    const mode = params.get('multi_doc_mode') as MultiDocMode | null

    if (docId) {
      setCatalogDocId(Number(docId))
      setQueryMode('rag')
    }
    if (docIds) {
      setMultiDocIds(docIds.split(',').map(Number))
      if (mode) setMultiDocMode(mode)
      setQueryMode('rag')
    }
  }, [])

  const handleSend = useCallback(
    async (question: string) => {
      if (!question.trim() || isLoading) return

      const userMsg: Message = {
        id: uuidv4(),
        role: 'user',
        content: question,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMsg])
      setIsLoading(true)

      try {
        const res = await sendChat({
          session_id: sessionId,
          question,
          mode: queryMode,
          doc_id: catalogDocId || undefined,
          doc_ids: multiDocIds.length > 0 ? multiDocIds : undefined,
          multi_doc_mode: multiDocIds.length > 0 ? multiDocMode : undefined,
        })

        const assistantMsg: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: res.answer,
          chartJson: res.chart_json,
          sqlQuery: res.sql_query,
          sources: res.sources,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, assistantMsg])
      } catch (err) {
        const errorMsg: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: `Error: ${err instanceof Error ? err.message : 'Something went wrong'}`,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, errorMsg])
      } finally {
        setIsLoading(false)
      }
    },
    [sessionId, queryMode, catalogDocId, multiDocIds, multiDocMode, isLoading]
  )

  const handleNewSession = () => {
    sessionStorage.removeItem('session_id')
    window.location.reload()
  }

  return (
    <div className="flex h-full">
      <ChatSidebar
        sessionId={sessionId}
        queryMode={queryMode}
        onQueryModeChange={setQueryMode}
        dataLoaded={dataLoaded}
        docLoaded={docLoaded}
        onDataLoaded={(info) => {
          setDataLoaded(true)
          setUploadedFile(info)
        }}
        onDocLoaded={(docId) => {
          setDocLoaded(true)
          if (docId) setCatalogDocId(docId)
        }}
        uploadedFile={uploadedFile}
        onNewSession={handleNewSession}
        multiDocIds={multiDocIds}
        multiDocMode={multiDocMode}
        onMultiDocModeChange={setMultiDocMode}
        onClearMultiDoc={() => setMultiDocIds([])}
        catalogDocId={catalogDocId}
        onClearCatalogDoc={() => setCatalogDocId(null)}
      />
      <div className="flex-1 flex flex-col overflow-hidden">
        <ChatMessages
          messages={messages}
          isLoading={isLoading}
          multiDocIds={multiDocIds}
          catalogDocId={catalogDocId}
        />
        <ChatInput onSend={handleSend} isLoading={isLoading} disabled={false} />
      </div>
    </div>
  )
}
