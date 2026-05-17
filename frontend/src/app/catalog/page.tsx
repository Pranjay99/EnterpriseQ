'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Search,
  Pin,
  Trash2,
  MessageSquare,
  Calendar,
  TrendingUp,
  BookOpen,
  BarChart2,
} from 'lucide-react'
import { getCatalogList, getCatalogStats, searchCatalog, pinDocument, deleteDocument } from '@/lib/api'
import type { CatalogItem, CatalogStats } from '@/types'
import { cn, formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useRouter } from 'next/navigation'

const CATEGORIES = [
  'All',
  'Finance',
  'HR',
  'Legal',
  'Technical',
  'Marketing',
  'Operations',
  'Research',
  'Other',
]

const SORT_OPTIONS = [
  { value: 'upload_date', label: 'Upload Date' },
  { value: 'query_count', label: 'Most Queried' },
  { value: 'last_accessed', label: 'Last Accessed' },
]

const CATEGORY_COLORS: Record<string, string> = {
  Finance: 'bg-green-500/20 text-green-400',
  HR: 'bg-blue-500/20 text-blue-400',
  Legal: 'bg-red-500/20 text-red-400',
  Technical: 'bg-purple-500/20 text-purple-400',
  Marketing: 'bg-orange-500/20 text-orange-400',
  Operations: 'bg-yellow-500/20 text-yellow-400',
  Research: 'bg-cyan-500/20 text-cyan-400',
  Other: 'bg-gray-500/20 text-gray-400',
}

export default function CatalogPage() {
  const router = useRouter()
  const [documents, setDocuments] = useState<CatalogItem[]>([])
  const [stats, setStats] = useState<CatalogStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All')
  const [sortBy, setSortBy] = useState('upload_date')
  const [pinnedOnly, setPinnedOnly] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [expandedSummary, setExpandedSummary] = useState<Set<number>>(new Set())
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    try {
      let data
      if (search.trim()) {
        data = await searchCatalog(search, category !== 'All' ? category : undefined)
        setDocuments(data.documents || data)
      } else {
        data = await getCatalogList({
          pinned_only: pinnedOnly,
          category: category !== 'All' ? category : undefined,
          sort_by: sortBy,
        })
        setDocuments(data.documents || data)
      }
    } catch {
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }, [search, category, sortBy, pinnedOnly])

  const loadStats = useCallback(async () => {
    try {
      const s = await getCatalogStats()
      setStats(s)
    } catch {
      // silently fail
    }
  }, [])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  const handlePin = async (docId: number, currentPinned: boolean) => {
    await pinDocument(docId, !currentPinned)
    loadDocuments()
    loadStats()
  }

  const handleDelete = async (docId: number) => {
    await deleteDocument(docId)
    setDeleteConfirm(null)
    loadDocuments()
    loadStats()
  }

  const handleChat = (docId: number) => {
    router.push(`/?doc_id=${docId}`)
  }

  const handleMultiChat = () => {
    const ids = Array.from(selected).join(',')
    router.push(`/?doc_ids=${ids}&multi_doc_mode=synthesize`)
  }

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSummary = (id: number) => {
    setExpandedSummary((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="flex h-full">
      {/* Filter Sidebar */}
      <aside className="w-56 border-r border-border p-4 flex flex-col gap-4 overflow-y-auto bg-card shrink-0">
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Search
          </p>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search docs..."
              className="pl-7 h-8 text-xs"
            />
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Category
          </p>
          <div className="space-y-1">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setCategory(c)}
                className={cn(
                  'w-full text-left text-xs px-2 py-1.5 rounded transition-colors',
                  category === c
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
                )}
              >
                {c}
                {stats && c !== 'All' && stats.category_breakdown[c] && (
                  <span className="float-right text-muted-foreground/60">
                    {stats.category_breakdown[c]}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Sort By
          </p>
          <Select value={sortBy} onValueChange={(v) => { if (v !== null) setSortBy(v) }}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <button
            onClick={() => setPinnedOnly((p) => !p)}
            className={cn(
              'flex items-center gap-2 text-xs px-2 py-1.5 rounded w-full transition-colors',
              pinnedOnly
                ? 'bg-yellow-500/20 text-yellow-400'
                : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
            )}
          >
            <Pin className="w-3.5 h-3.5" /> Pinned Only
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Stats Bar */}
        {stats && (
          <div className="border-b border-border bg-card px-6 py-3 flex gap-6 shrink-0">
            {[
              { label: 'Documents', value: stats.total_documents, icon: BookOpen },
              { label: 'Total Queries', value: stats.total_queries, icon: TrendingUp },
              { label: 'Pinned', value: stats.pinned_count, icon: Pin },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="flex items-center gap-2">
                <Icon className="w-4 h-4 text-muted-foreground" />
                <div>
                  <p className="text-lg font-bold leading-none">{value}</p>
                  <p className="text-[10px] text-muted-foreground">{label}</p>
                </div>
              </div>
            ))}
            {stats.most_queried && (
              <div className="flex items-center gap-2 ml-auto">
                <BarChart2 className="w-4 h-4 text-muted-foreground" />
                <div>
                  <p className="text-xs font-medium truncate max-w-32">{stats.most_queried.filename}</p>
                  <p className="text-[10px] text-muted-foreground">Most queried</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Multi-select bar */}
        {selected.size > 0 && (
          <div className="px-6 py-2 bg-primary/10 border-b border-primary/20 flex items-center gap-3">
            <span className="text-xs text-primary font-medium">{selected.size} selected</span>
            <Button size="sm" onClick={handleMultiChat} className="h-7 text-xs gap-1">
              <MessageSquare className="w-3 h-3" /> Chat with selected
            </Button>
            <button
              onClick={() => setSelected(new Set())}
              className="text-xs text-muted-foreground hover:text-foreground ml-auto"
            >
              Clear
            </button>
          </div>
        )}

        {/* Document Grid */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-48 text-muted-foreground">
              Loading documents...
            </div>
          ) : documents.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
              <BookOpen className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm">No documents found</p>
              <p className="text-xs mt-1 opacity-60">
                Upload PDFs on the Chat page to populate the catalog
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className={cn(
                    'rounded-xl border bg-card p-4 flex flex-col gap-3 transition-colors',
                    selected.has(doc.id)
                      ? 'border-primary/50 bg-primary/5'
                      : 'border-border hover:border-border/80'
                  )}
                >
                  {/* Header */}
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={selected.has(doc.id)}
                      onChange={() => toggleSelect(doc.id)}
                      className="mt-0.5 accent-blue-500"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-1">
                        {doc.is_pinned && (
                          <Pin className="w-3 h-3 text-yellow-400 shrink-0" />
                        )}
                        <p className="text-sm font-medium truncate">{doc.filename}</p>
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className={cn(
                            'text-[10px] px-1.5 py-0.5 rounded font-medium',
                            CATEGORY_COLORS[doc.category] || CATEGORY_COLORS.Other
                          )}
                        >
                          {doc.category}
                        </span>
                        {doc.tags?.slice(0, 2).map((tag) => (
                          <span
                            key={tag}
                            className="text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="flex-1">
                    <p
                      className={cn(
                        'text-xs text-muted-foreground leading-relaxed',
                        !expandedSummary.has(doc.id) && 'line-clamp-3'
                      )}
                    >
                      {doc.summary}
                    </p>
                    {doc.summary && doc.summary.length > 120 && (
                      <button
                        onClick={() => toggleSummary(doc.id)}
                        className="text-[10px] text-primary mt-1 hover:underline"
                      >
                        {expandedSummary.has(doc.id) ? 'Show less' : 'Read more'}
                      </button>
                    )}
                  </div>

                  {/* Meta */}
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" /> {formatDate(doc.upload_date)}
                    </span>
                    <span className="flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" /> {doc.query_count} queries
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 pt-2 border-t border-border">
                    <button
                      onClick={() => handlePin(doc.id, doc.is_pinned)}
                      className={cn(
                        'p-1.5 rounded hover:bg-secondary transition-colors',
                        doc.is_pinned ? 'text-yellow-400' : 'text-muted-foreground'
                      )}
                      title={doc.is_pinned ? 'Unpin' : 'Pin'}
                    >
                      <Pin className="w-3.5 h-3.5" />
                    </button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleChat(doc.id)}
                      className="flex-1 h-7 text-xs gap-1"
                    >
                      <MessageSquare className="w-3 h-3" /> Chat
                    </Button>
                    {deleteConfirm === doc.id ? (
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="text-[10px] text-destructive hover:underline px-1"
                        >
                          Confirm
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(null)}
                          className="text-[10px] text-muted-foreground hover:underline px-1"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setDeleteConfirm(doc.id)}
                        className="p-1.5 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
