'use client'

import { useState, useCallback, useEffect, useMemo } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { ChatSidebar } from '@/components/chat/ChatSidebar'
import { ChatTopBar } from '@/components/chat/ChatTopBar'
import { ChatMessages } from '@/components/chat/ChatMessages'
import { ChatInput } from '@/components/chat/ChatInput'
import { sendChat, getCatalogList, loadCatalogDoc } from '@/lib/api'
import { generateSessionId } from '@/lib/utils'
import type { Message, QueryMode, MultiDocMode, UploadResponse, CatalogItem } from '@/types'

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string>('')

  useEffect(() => {
    const stored = sessionStorage.getItem('session_id')
    if (stored) {
      setSessionId(stored)
    } else {
      const id = generateSessionId()
      sessionStorage.setItem('session_id', id)
      setSessionId(id)
    }
  }, [])

  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [queryMode, setQueryMode] = useState<QueryMode>('auto')

  // All files uploaded this session (data files + PDFs)
  const [attachments, setAttachments] = useState<UploadResponse[]>([])
  // Documents picked from the catalog
  const [catalogDocs, setCatalogDocs] = useState<CatalogItem[]>([])
  // Universal chat toggle: route questions to the selected documents
  const [chatWithDocs, setChatWithDocs] = useState(false)
  const [multiDocMode, setMultiDocMode] = useState<MultiDocMode>('synthesize')

  // Unique doc ids usable for document chat (only embedded documents — PDFs).
  // Cataloged data files are loaded as session tables instead.
  const docIds = useMemo(() => {
    const ids = [
      ...attachments
        .filter((a) => a.file_type === 'document' && a.doc_id != null)
        .map((a) => a.doc_id as number),
      ...catalogDocs.filter((c) => c.file_type === 'pdf').map((c) => c.id),
    ]
    return Array.from(new Set(ids))
  }, [attachments, catalogDocs])

  // Read URL params for catalog/multi-doc selections (links from other pages)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const single = params.get('doc_id')
    const multi = params.get('doc_ids')
    const mode = params.get('multi_doc_mode') as MultiDocMode | null

    const ids = [
      ...(single ? [Number(single)] : []),
      ...(multi ? multi.split(',').map(Number) : []),
    ].filter((n) => !Number.isNaN(n))
    if (ids.length === 0) return

    if (mode) setMultiDocMode(mode)
    getCatalogList()
      .then((res) => {
        const picked = res.documents.filter((d) => ids.includes(d.id) && d.file_type === 'pdf')
        if (picked.length > 0) {
          setCatalogDocs(picked)
          setChatWithDocs(true)
        }
      })
      .catch(() => {
        // Catalog fetch failed (e.g. not signed in yet) — user can re-pick manually
      })
  }, [])

  const handleSend = useCallback(
    async (question: string) => {
      if (!question.trim() || isLoading || !sessionId) return

      const userMsg: Message = {
        id: uuidv4(),
        role: 'user',
        content: question,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMsg])
      setIsLoading(true)

      const useDocs = chatWithDocs && docIds.length > 0

      try {
        const res = await sendChat({
          session_id: sessionId,
          question,
          mode: queryMode,
          doc_id: useDocs && docIds.length === 1 ? docIds[0] : undefined,
          doc_ids: useDocs && docIds.length > 1 ? docIds : undefined,
          multi_doc_mode: useDocs && docIds.length > 1 ? multiDocMode : undefined,
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
    [sessionId, queryMode, chatWithDocs, docIds, multiDocMode, isLoading]
  )

  const handleUploaded = (res: UploadResponse) => {
    setAttachments((prev) => [
      // Re-uploading the same filename replaces its entry (and its SQL table)
      ...prev.filter((a) => a.filename !== res.filename),
      res,
    ])
  }

  // Merge catalog metadata into a session attachment after "Add to catalog"
  const handleCataloged = (filename: string, res: UploadResponse) => {
    setAttachments((prev) =>
      prev.map((a) =>
        a.filename === filename
          ? { ...a, doc_id: res.doc_id, category: res.category, tags: res.tags, summary: res.summary }
          : a
      )
    )
  }

  // Load cataloged data files passed via URL (e.g. Chat button on catalog page)
  useEffect(() => {
    if (!sessionId) return
    const params = new URLSearchParams(window.location.search)
    const loadIds = (params.get('load_doc_ids') ?? '')
      .split(',')
      .map(Number)
      .filter((n) => !Number.isNaN(n) && n > 0)
    if (loadIds.length === 0) return
    ;(async () => {
      for (const id of loadIds) {
        try {
          const res = await loadCatalogDoc(id, sessionId)
          handleUploaded(res)
        } catch {
          // Skip entries that fail to load (deleted, not data, etc.)
        }
      }
    })()
  }, [sessionId])

  const handleNewSession = () => {
    sessionStorage.removeItem('session_id')
    window.location.reload()
  }

  return (
    <div className="flex h-full">
      <ChatSidebar
        sessionId={sessionId}
        attachments={attachments}
        catalogDocs={catalogDocs}
        onUploaded={handleUploaded}
        onCataloged={handleCataloged}
        onAddCatalogDocs={(docs) =>
          setCatalogDocs((prev) => {
            const existing = new Set(prev.map((d) => d.id))
            return [...prev, ...docs.filter((d) => !existing.has(d.id))]
          })
        }
        onRemoveCatalogDoc={(id) =>
          setCatalogDocs((prev) => prev.filter((d) => d.id !== id))
        }
        onNewSession={handleNewSession}
      />
      <div className="flex-1 flex flex-col overflow-hidden">
        <ChatTopBar
          docCount={docIds.length}
          chatWithDocs={chatWithDocs}
          onToggleChatWithDocs={() => setChatWithDocs((v) => !v)}
          multiDocMode={multiDocMode}
          onMultiDocModeChange={setMultiDocMode}
        />
        <ChatMessages
          messages={messages}
          isLoading={isLoading}
          docCount={docIds.length}
          chatWithDocs={chatWithDocs}
        />
        <ChatInput
          onSend={handleSend}
          isLoading={isLoading}
          disabled={!sessionId}
          queryMode={queryMode}
          onQueryModeChange={setQueryMode}
        />
      </div>
    </div>
  )
}
