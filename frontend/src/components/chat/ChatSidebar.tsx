'use client'

import { useRef, useState } from 'react'
import {
  Upload, RefreshCw, FileSpreadsheet, FileText, X,
  ChevronDown, ChevronRight, BookOpen, Loader2, BookmarkPlus, BookmarkCheck,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { uploadFile, getCatalogList, addTableToCatalog, loadCatalogDoc } from '@/lib/api'
import type { UploadResponse, CatalogItem } from '@/types'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'

interface Props {
  sessionId: string
  attachments: UploadResponse[]
  catalogDocs: CatalogItem[]
  onUploaded: (res: UploadResponse) => void
  onCataloged: (filename: string, res: UploadResponse) => void
  onAddCatalogDocs: (docs: CatalogItem[]) => void
  onRemoveCatalogDoc: (id: number) => void
  onNewSession: () => void
}

function TypeBadge({ type }: { type?: string }) {
  return (
    <span
      className={cn(
        'text-[9px] px-1.5 py-0.5 rounded-full shrink-0 font-medium',
        type === 'number'
          ? 'bg-blue-500/15 text-blue-400'
          : type === 'datetime'
          ? 'bg-purple-500/15 text-purple-400'
          : type === 'boolean'
          ? 'bg-amber-500/15 text-amber-400'
          : 'bg-green-500/15 text-green-400'
      )}
    >
      {type ?? 'text'}
    </span>
  )
}

/** Expandable row for a file uploaded this session. */
function UploadRow({
  item,
  isActiveData,
  onAddToCatalog,
}: {
  item: UploadResponse
  isActiveData?: boolean
  onAddToCatalog?: () => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [cataloging, setCataloging] = useState(false)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const isDoc = item.file_type === 'document'
  const inCatalog = item.doc_id != null

  const handleAddToCatalog = async () => {
    if (!onAddToCatalog || cataloging) return
    setCataloging(true)
    setCatalogError(null)
    try {
      await onAddToCatalog()
    } catch (e) {
      setCatalogError(e instanceof Error ? e.message : 'Failed to add to catalog')
    } finally {
      setCataloging(false)
    }
  }

  return (
    <div className="rounded-lg border border-border bg-secondary/40 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 p-2.5 hover:bg-secondary/80 transition-colors text-left"
      >
        {isDoc ? (
          <FileText className="w-4 h-4 text-orange-400 shrink-0" />
        ) : (
          <FileSpreadsheet className="w-4 h-4 text-green-400 shrink-0" />
        )}
        <span className="text-xs font-medium truncate flex-1" title={item.filename}>
          {item.filename}
        </span>
        {inCatalog && (
          <BookmarkCheck
            className="w-3.5 h-3.5 text-primary shrink-0"
            aria-label="In catalog"
          />
        )}
        {isActiveData && (
          <span
            title="Active table for DataFrame analysis & charts (most recent data file)"
            className="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0"
          />
        )}
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        )}
      </button>

      {open && (
        <div className="px-2.5 pb-2.5 space-y-2 border-t border-border/60 pt-2">
          {/* Stats */}
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            {item.rows != null && (
              <span className="text-[10px] text-muted-foreground">
                <span className="font-semibold text-foreground">{item.rows.toLocaleString()}</span> rows
              </span>
            )}
            {item.columns != null && (
              <span className="text-[10px] text-muted-foreground">
                <span className="font-semibold text-foreground">{item.columns.length}</span> columns
              </span>
            )}
            {item.chunks != null && (
              <span className="text-[10px] text-muted-foreground">
                <span className="font-semibold text-foreground">{item.chunks}</span> chunks
              </span>
            )}
            {item.size_mb != null && (
              <span className="text-[10px] text-muted-foreground">
                <span className="font-semibold text-foreground">{item.size_mb}</span> MB
              </span>
            )}
          </div>

          {/* Data files: SQL table name */}
          {item.table_name && (
            <p className="text-[10px] text-muted-foreground">
              SQL table: <code className="bg-secondary px-1 py-0.5 rounded text-foreground">{item.table_name}</code>
            </p>
          )}

          {/* Data files: columns with types */}
          {item.columns != null && item.columns.length > 0 && (
            <div className="max-h-40 overflow-y-auto space-y-1">
              {item.columns.map((col) => (
                <div key={col} className="flex items-center justify-between gap-2">
                  <span className="text-[11px] text-foreground truncate" title={col}>
                    {col}
                  </span>
                  <TypeBadge type={item.column_types?.[col]} />
                </div>
              ))}
            </div>
          )}

          {/* Catalog metadata (PDFs always; data files once cataloged) */}
          {(item.category || (item.tags && item.tags.length > 0) || item.summary) && (
            <div className="space-y-1.5">
              {item.category && (
                <span className="inline-block text-[9px] px-2 py-0.5 rounded-full bg-orange-500/15 text-orange-400 font-medium">
                  {item.category}
                </span>
              )}
              {item.tags && item.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {item.tags.map((t) => (
                    <span key={t} className="text-[9px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground">
                      #{t}
                    </span>
                  ))}
                </div>
              )}
              {item.summary && (
                <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-4" title={item.summary}>
                  {item.summary}
                </p>
              )}
            </div>
          )}

          {/* Add to catalog (data files not yet cataloged) */}
          {!isDoc && !inCatalog && onAddToCatalog && (
            <div>
              <Button
                size="sm"
                variant="outline"
                onClick={handleAddToCatalog}
                disabled={cataloging}
                className="h-7 w-full gap-1.5 text-[11px]"
              >
                {cataloging ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" /> Adding to catalog…
                  </>
                ) : (
                  <>
                    <BookmarkPlus className="w-3 h-3" /> Add to catalog
                  </>
                )}
              </Button>
              {catalogError && (
                <p className="text-[10px] text-destructive mt-1">{catalogError}</p>
              )}
            </div>
          )}
          {!isDoc && inCatalog && (
            <p className="text-[10px] text-primary flex items-center gap-1">
              <BookmarkCheck className="w-3 h-3" /> Saved in catalog
            </p>
          )}
        </div>
      )}
    </div>
  )
}

/** Expandable row for a document picked from the catalog. */
function CatalogRow({ item, onRemove }: { item: CatalogItem; onRemove: () => void }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-lg border border-purple-500/25 bg-secondary/40 overflow-hidden">
      <div className="flex items-center gap-1 pr-1.5 hover:bg-secondary/80 transition-colors">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-2 p-2.5 flex-1 min-w-0 text-left"
        >
          <BookOpen className="w-4 h-4 text-purple-400 shrink-0" />
          <span className="text-xs font-medium truncate flex-1" title={item.filename}>
            {item.filename}
          </span>
          {open ? (
            <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          )}
        </button>
        <button
          onClick={onRemove}
          title="Remove from selection"
          className="p-1 rounded text-muted-foreground hover:text-destructive shrink-0"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {open && (
        <div className="px-2.5 pb-2.5 space-y-1.5 border-t border-border/60 pt-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-400 font-medium">
              {item.category || 'Uncategorized'}
            </span>
            <span className="text-[10px] text-muted-foreground">
              queried <span className="font-semibold text-foreground">{item.query_count}</span>×
            </span>
          </div>
          {item.tags && item.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {item.tags.map((t) => (
                <span key={t} className="text-[9px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground">
                  #{t}
                </span>
              ))}
            </div>
          )}
          {item.summary && (
            <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-4" title={item.summary}>
              {item.summary}
            </p>
          )}
          <p className="text-[9px] text-muted-foreground/60">
            Uploaded {new Date(item.upload_date).toLocaleDateString()}
          </p>
        </div>
      )}
    </div>
  )
}

export function ChatSidebar({
  sessionId,
  attachments,
  catalogDocs,
  onUploaded,
  onCataloged,
  onAddCatalogDocs,
  onRemoveCatalogDoc,
  onNewSession,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // "Add from catalog" dialog state
  const [pickerOpen, setPickerOpen] = useState(false)
  const [pickerLoading, setPickerLoading] = useState(false)
  const [pickerDocs, setPickerDocs] = useState<CatalogItem[]>([])
  const [pickerSelected, setPickerSelected] = useState<Set<number>>(new Set())

  const alreadyAdded = new Set([
    ...attachments.filter((a) => a.doc_id != null).map((a) => a.doc_id as number),
    ...catalogDocs.map((d) => d.id),
  ])

  const handleFiles = async (files: FileList | File[]) => {
    const list = Array.from(files)
    if (list.length === 0) return
    if (!sessionId) {
      setError('Session is still initialising — please try again.')
      return
    }
    setUploading(true)
    setError(null)
    const failures: string[] = []

    // Upload sequentially — PDF ingestion is heavy (embedding + summary),
    // so parallel uploads would just contend for the same backend worker.
    for (let i = 0; i < list.length; i++) {
      const file = list[i]
      setUploadProgress(list.length > 1 ? `Uploading ${i + 1}/${list.length}: ${file.name}` : `Uploading ${file.name}…`)
      try {
        const res = await uploadFile(sessionId, file)
        onUploaded(res)
      } catch (e) {
        failures.push(`${file.name}: ${e instanceof Error ? e.message : 'upload failed'}`)
      }
    }

    setUploadProgress(null)
    setUploading(false)
    if (failures.length > 0) setError(failures.join(' · '))
  }

  const openPicker = async () => {
    setPickerOpen(true)
    setPickerLoading(true)
    setPickerSelected(new Set())
    try {
      const res = await getCatalogList()
      setPickerDocs(res.documents)
    } catch {
      setPickerDocs([])
    } finally {
      setPickerLoading(false)
    }
  }

  const [pickerAdding, setPickerAdding] = useState(false)

  const confirmPicker = async () => {
    const chosen = pickerDocs.filter((d) => pickerSelected.has(d.id))
    // PDFs join document chat; data files are loaded into the session as tables
    onAddCatalogDocs(chosen.filter((d) => d.file_type === 'pdf'))
    const dataDocs = chosen.filter((d) => d.file_type !== 'pdf')
    if (dataDocs.length > 0) {
      setPickerAdding(true)
      for (const d of dataDocs) {
        try {
          const res = await loadCatalogDoc(d.id, sessionId)
          onUploaded(res)
        } catch {
          // Skip entries that fail to load
        }
      }
      setPickerAdding(false)
    }
    setPickerOpen(false)
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
            if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files)
          }}
        >
          <Upload className="w-6 h-6 mx-auto mb-2 text-muted-foreground" />
          <p className="text-xs text-muted-foreground">
            {uploading ? (uploadProgress ?? 'Uploading...') : 'Drop files or click to browse'}
          </p>
          <p className="text-[10px] text-muted-foreground/60 mt-1">
            CSV · XLSX · JSON · PDF — multiple files supported
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".csv,.xlsx,.xls,.json,.pdf"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) handleFiles(e.target.files)
            e.target.value = ''
          }}
        />
        {error && <p className="text-xs text-destructive mt-2">{error}</p>}
      </div>

      {/* Documents */}
      <div className="p-4 space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Documents
            {attachments.length + catalogDocs.length > 0 && (
              <span className="ml-1.5 text-primary">({attachments.length + catalogDocs.length})</span>
            )}
          </p>
          <Button variant="ghost" size="sm" onClick={openPicker} className="h-7 gap-1 text-xs">
            <BookOpen className="w-3 h-3" /> Catalog
          </Button>
        </div>

        {attachments.length === 0 && catalogDocs.length === 0 && (
          <p className="text-[11px] text-muted-foreground/60">
            Upload files or add documents from your catalog. Click a document to see its details.
          </p>
        )}

        {attachments.map((a, i) => (
          <UploadRow
            key={a.filename}
            item={a}
            isActiveData={
              a.file_type === 'data' &&
              i === attachments.map((x) => x.file_type).lastIndexOf('data')
            }
            onAddToCatalog={
              a.file_type === 'data' && a.table_name
                ? async () => {
                    const res = await addTableToCatalog(sessionId, a.table_name!, a.filename)
                    onCataloged(a.filename, res)
                  }
                : undefined
            }
          />
        ))}
        {catalogDocs.map((d) => (
          <CatalogRow key={d.id} item={d} onRemove={() => onRemoveCatalogDoc(d.id)} />
        ))}
      </div>

      <div className="mt-auto p-4">
        <p className="text-[10px] text-muted-foreground/40 text-center">Enterprise Q v1.0</p>
      </div>

      {/* Add-from-catalog dialog */}
      <Dialog open={pickerOpen} onOpenChange={setPickerOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add documents from catalog</DialogTitle>
          </DialogHeader>
          {pickerLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-primary" />
            </div>
          ) : pickerDocs.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">
              No documents in your catalog yet. Upload a PDF to add one.
            </p>
          ) : (
            <div className="max-h-72 overflow-y-auto space-y-1.5 py-1">
              {pickerDocs.map((d) => {
                const added = alreadyAdded.has(d.id)
                const checked = pickerSelected.has(d.id)
                return (
                  <button
                    key={d.id}
                    disabled={added}
                    onClick={() =>
                      setPickerSelected((prev) => {
                        const next = new Set(prev)
                        if (next.has(d.id)) next.delete(d.id)
                        else next.add(d.id)
                        return next
                      })
                    }
                    className={cn(
                      'w-full flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-colors',
                      added
                        ? 'border-border opacity-40 cursor-not-allowed'
                        : checked
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/40'
                    )}
                  >
                    <div
                      className={cn(
                        'w-4 h-4 rounded border flex items-center justify-center shrink-0',
                        checked ? 'bg-primary border-primary' : 'border-muted-foreground/40'
                      )}
                    >
                      {checked && <span className="text-[10px] text-primary-foreground leading-none">✓</span>}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium truncate">{d.filename}</p>
                      <p className="text-[10px] text-muted-foreground truncate">
                        {d.file_type === 'pdf' ? 'document' : `${d.file_type} · loads as table`}
                        {' · '}
                        {d.category || 'Uncategorized'}
                        {added && ' · already added'}
                      </p>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" size="sm" onClick={() => setPickerOpen(false)} disabled={pickerAdding}>
              Cancel
            </Button>
            <Button size="sm" onClick={confirmPicker} disabled={pickerSelected.size === 0 || pickerAdding}>
              {pickerAdding ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin mr-1" /> Loading…
                </>
              ) : (
                <>Add {pickerSelected.size > 0 ? `(${pickerSelected.size})` : ''}</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  )
}
