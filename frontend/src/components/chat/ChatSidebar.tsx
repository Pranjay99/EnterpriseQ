'use client'

import { useRef, useState } from 'react'
import { Upload, RefreshCw, FileSpreadsheet, FileText, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { uploadFile } from '@/lib/api'
import type { QueryMode, MultiDocMode } from '@/types'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const QUERY_MODES: { value: QueryMode; label: string; description: string; icon: string }[] = [
  { value: 'sql', label: 'Text-to-SQL', description: 'Query structured data', icon: '🗄️' },
  { value: 'dataframe', label: 'DataFrame Analysis', description: 'Pandas-powered analysis', icon: '📊' },
  { value: 'rag', label: 'Document Q&A', description: 'RAG over documents', icon: '📄' },
  { value: 'general', label: 'Math & Reasoning', description: 'Calculations & logic', icon: '🧮' },
]

interface Props {
  sessionId: string
  queryMode: QueryMode
  onQueryModeChange: (m: QueryMode) => void
  dataLoaded: boolean
  docLoaded: boolean
  onDataLoaded: (info: { name: string; rows?: number; columns?: number }) => void
  onDocLoaded: (docId?: number) => void
  uploadedFile: { name: string; rows?: number; columns?: number; chunks?: number } | null
  onNewSession: () => void
  multiDocIds: number[]
  multiDocMode: MultiDocMode
  onMultiDocModeChange: (m: MultiDocMode) => void
  onClearMultiDoc: () => void
  catalogDocId: number | null
  onClearCatalogDoc: () => void
}

export function ChatSidebar({
  sessionId,
  queryMode,
  onQueryModeChange,
  onDataLoaded,
  onDocLoaded,
  uploadedFile,
  onNewSession,
  multiDocIds,
  multiDocMode,
  onMultiDocModeChange,
  onClearMultiDoc,
  catalogDocId,
  onClearCatalogDoc,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = async (file: File) => {
    setUploading(true)
    setError(null)
    try {
      const res = await uploadFile(sessionId, file)
      if (res.file_type === 'data') {
        onDataLoaded({ name: res.filename, rows: res.rows, columns: res.columns })
      } else {
        onDocLoaded(res.doc_id)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <aside className="w-72 flex flex-col border-r border-border bg-card overflow-y-auto shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-semibold text-foreground">Session</span>
          <Button variant="ghost" size="sm" onClick={onNewSession} className="h-7 gap-1 text-xs">
            <RefreshCw className="w-3 h-3" /> New
          </Button>
        </div>
        <code className="text-xs text-muted-foreground font-mono bg-secondary px-2 py-1 rounded block truncate">
          {sessionId}
        </code>
      </div>

      {/* File Upload */}
      <div className="p-4 border-b border-border">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          Upload Data
        </p>
        <div
          className={cn(
            'border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors',
            dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50',
            uploading && 'opacity-50 pointer-events-none'
          )}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            const f = e.dataTransfer.files[0]
            if (f) handleFile(f)
          }}
        >
          <Upload className="w-6 h-6 mx-auto mb-2 text-muted-foreground" />
          <p className="text-xs text-muted-foreground">
            {uploading ? 'Uploading...' : 'Drop file or click to browse'}
          </p>
          <p className="text-[10px] text-muted-foreground/60 mt-1">CSV · XLSX · JSON · PDF</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls,.json,.pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) handleFile(f)
          }}
        />
        {error && <p className="text-xs text-destructive mt-2">{error}</p>}

        {/* Uploaded file info */}
        {uploadedFile && (
          <div className="mt-3 p-3 rounded-lg bg-secondary/50 border border-border">
            <div className="flex items-center gap-2">
              {uploadedFile.chunks !== undefined ? (
                <FileText className="w-4 h-4 text-orange-400 shrink-0" />
              ) : (
                <FileSpreadsheet className="w-4 h-4 text-green-400 shrink-0" />
              )}
              <span className="text-xs font-medium truncate">{uploadedFile.name}</span>
            </div>
            <div className="flex gap-3 mt-2">
              {uploadedFile.rows !== undefined && (
                <span className="text-[10px] text-muted-foreground">
                  {uploadedFile.rows.toLocaleString()} rows
                </span>
              )}
              {uploadedFile.columns !== undefined && (
                <span className="text-[10px] text-muted-foreground">
                  {uploadedFile.columns} cols
                </span>
              )}
              {uploadedFile.chunks !== undefined && (
                <span className="text-[10px] text-muted-foreground">
                  {uploadedFile.chunks} chunks
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Query Mode */}
      <div className="p-4 border-b border-border">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          Query Mode
        </p>
        <div className="space-y-1">
          {QUERY_MODES.map((m) => (
            <button
              key={m.value}
              onClick={() => onQueryModeChange(m.value)}
              className={cn(
                'w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center gap-2',
                queryMode === m.value
                  ? 'bg-primary/20 text-primary border border-primary/30'
                  : 'hover:bg-secondary text-muted-foreground hover:text-foreground border border-transparent'
              )}
            >
              <span className="text-base">{m.icon}</span>
              <div>
                <p className="text-xs font-medium">{m.label}</p>
                <p className="text-[10px] text-muted-foreground">{m.description}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Multi-doc indicator */}
      {multiDocIds.length > 0 && (
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-blue-400 uppercase tracking-wide">
              Multi-Doc Mode
            </p>
            <button
              onClick={onClearMultiDoc}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <p className="text-xs text-muted-foreground mb-2">
            {multiDocIds.length} documents selected
          </p>
          <Select
            value={multiDocMode}
            onValueChange={(v) => { if (v !== null) onMultiDocModeChange(v as MultiDocMode) }}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="synthesize">Synthesize</SelectItem>
              <SelectItem value="compare">Compare</SelectItem>
              <SelectItem value="per_doc">Per Document</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Catalog doc indicator */}
      {catalogDocId && (
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold text-purple-400 uppercase tracking-wide">
              Catalog Doc
            </p>
            <button
              onClick={onClearCatalogDoc}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <p className="text-xs text-muted-foreground">Doc ID: {catalogDocId}</p>
        </div>
      )}

      <div className="mt-auto p-4">
        <p className="text-[10px] text-muted-foreground/40 text-center">Enterprise Q v1.0</p>
      </div>
    </aside>
  )
}
