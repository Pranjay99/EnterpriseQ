'use client'

import { useState, useEffect, useCallback } from 'react'
import { getCatalogList, queryMultiDoc } from '@/lib/api'
import type { CatalogItem, MultiDocMode } from '@/types'
import { cn, formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Loader2,
  FileText,
  CheckSquare,
  Square,
  Sparkles,
  GitCompare,
  AlignLeft,
  Send,
} from 'lucide-react'

const MODES: {
  value: MultiDocMode
  label: string
  description: string
  icon: React.ReactNode
}[] = [
  {
    value: 'synthesize',
    label: 'Synthesize',
    description: 'Combine documents into one unified answer',
    icon: <Sparkles className="w-5 h-5" />,
  },
  {
    value: 'compare',
    label: 'Compare',
    description: 'Highlight similarities and differences',
    icon: <GitCompare className="w-5 h-5" />,
  },
  {
    value: 'per_doc',
    label: 'Per Document',
    description: 'Answer separately for each document',
    icon: <AlignLeft className="w-5 h-5" />,
  },
]

interface MultiDocResult {
  answer: string
  sources: string[]
  mode: string
}

export default function MultiDocPage() {
  const [documents, setDocuments] = useState<CatalogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [mode, setMode] = useState<MultiDocMode>('synthesize')
  const [question, setQuestion] = useState('')
  const [answering, setAnswering] = useState(false)
  const [result, setResult] = useState<MultiDocResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadDocs = useCallback(async () => {
    try {
      const data = await getCatalogList()
      setDocuments(data.documents || data)
    } catch {
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDocs()
  }, [loadDocs])

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else if (next.size < 10) next.add(id)
      return next
    })
  }

  const handleSubmit = async () => {
    if (!question.trim() || selected.size === 0) return
    setAnswering(true)
    setError(null)
    setResult(null)
    try {
      const res = await queryMultiDoc({
        doc_ids: Array.from(selected),
        question: question.trim(),
        mode,
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Query failed')
    } finally {
      setAnswering(false)
    }
  }

  const canSubmit = selected.size > 0 && question.trim().length > 0 && !answering

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Multi-Document Analysis</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Query and synthesize insights across multiple documents
          </p>
        </div>

        {/* Step 1: Select Documents */}
        <section className="rounded-xl border border-border bg-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div
              className={cn(
                'w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold',
                selected.size > 0
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-muted-foreground'
              )}
            >
              1
            </div>
            <div>
              <h2 className="text-sm font-semibold">Select Documents</h2>
              <p className="text-xs text-muted-foreground">
                Choose 2–10 documents to analyze together
              </p>
            </div>
            {selected.size > 0 && (
              <span className="ml-auto text-xs text-primary font-medium">
                {selected.size} selected
              </span>
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-24 text-muted-foreground">
              <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading documents...
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No documents in catalog. Upload PDFs on the Chat page first.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {documents.map((doc) => {
                const isSelected = selected.has(doc.id)
                const disabled = !isSelected && selected.size >= 10
                return (
                  <button
                    key={doc.id}
                    onClick={() => !disabled && toggleSelect(doc.id)}
                    disabled={disabled}
                    className={cn(
                      'text-left p-3 rounded-lg border transition-colors flex items-start gap-2',
                      isSelected
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/50 bg-secondary/30',
                      disabled && 'opacity-40 cursor-not-allowed'
                    )}
                  >
                    {isSelected ? (
                      <CheckSquare className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                    ) : (
                      <Square className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                    )}
                    <div className="min-w-0">
                      <p className="text-xs font-medium truncate">{doc.filename}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {doc.category} · {formatDate(doc.upload_date)}
                      </p>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </section>

        {/* Step 2: Select Mode */}
        <section className="rounded-xl border border-border bg-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-7 h-7 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-bold">
              2
            </div>
            <div>
              <h2 className="text-sm font-semibold">Select Analysis Mode</h2>
              <p className="text-xs text-muted-foreground">
                How should the AI approach this query?
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {MODES.map((m) => (
              <button
                key={m.value}
                onClick={() => setMode(m.value)}
                className={cn(
                  'p-4 rounded-lg border text-left transition-colors',
                  mode === m.value
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:border-primary/50'
                )}
              >
                <div
                  className={cn('mb-2', mode === m.value ? 'text-primary' : 'text-muted-foreground')}
                >
                  {m.icon}
                </div>
                <p className="text-sm font-medium">{m.label}</p>
                <p className="text-xs text-muted-foreground mt-1">{m.description}</p>
              </button>
            ))}
          </div>
        </section>

        {/* Step 3: Ask Question */}
        <section className="rounded-xl border border-border bg-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div
              className={cn(
                'w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold',
                canSubmit
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-muted-foreground'
              )}
            >
              3
            </div>
            <div>
              <h2 className="text-sm font-semibold">Ask Your Question</h2>
              <p className="text-xs text-muted-foreground">
                What would you like to know across these documents?
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. What are the main risks mentioned? How do the financial projections compare?"
              rows={3}
              className="flex-1 bg-secondary rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground resize-none outline-none border border-border focus:border-primary/50 transition-colors"
            />
            <Button onClick={handleSubmit} disabled={!canSubmit} className="gap-2 self-end">
              {answering ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              Analyze
            </Button>
          </div>
        </section>

        {/* Result */}
        {(result || error || answering) && (
          <section className="rounded-xl border border-border bg-card p-6">
            <h2 className="text-sm font-semibold mb-3">
              {answering ? 'Analyzing...' : 'Analysis Result'}
              {result && (
                <span className="ml-2 text-xs text-muted-foreground font-normal capitalize">
                  ({result.mode.replace('_', ' ')})
                </span>
              )}
            </h2>

            {answering && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                <span className="text-sm">Processing {selected.size} documents...</span>
              </div>
            )}

            {error && <p className="text-sm text-destructive">{error}</p>}

            {result && (
              <div className="space-y-4">
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{result.answer}</p>
                {result.sources && result.sources.length > 0 && (
                  <details>
                    <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground flex items-center gap-1">
                      <FileText className="w-3 h-3" /> Sources ({result.sources.length})
                    </summary>
                    <ul className="mt-2 space-y-1">
                      {result.sources.map((s, i) => (
                        <li
                          key={i}
                          className="text-xs bg-secondary px-2 py-1 rounded text-muted-foreground"
                        >
                          {s}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  )
}
