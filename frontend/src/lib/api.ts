import type {
  ChatRequest,
  ChatResponse,
  CatalogListResponse,
  CatalogStats,
  MultiDocMode,
  MultiDocResponse,
  UploadResponse,
} from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Unwrap a fetch Response: on error, surface FastAPI's `detail` message
 * (never the raw response body, which may contain internals).
 */
async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed with status ${res.status}`
    try {
      const data = await res.json()
      if (typeof data?.detail === 'string') message = data.detail
    } catch {
      // Non-JSON error body — keep the generic message
    }
    throw new Error(message)
  }
  return res.json() as Promise<T>
}

export async function uploadFile(sessionId: string, file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/upload/${sessionId}`, {
    method: 'POST',
    body: formData,
  })
  return handleResponse<UploadResponse>(res)
}

export async function clearSession(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/upload/${sessionId}`, { method: 'DELETE' })
  return handleResponse<{ message: string }>(res)
}

export async function sendChat(body: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return handleResponse<ChatResponse>(res)
}

export async function getCatalogList(params?: {
  pinned_only?: boolean
  category?: string
  sort_by?: string
}) {
  const url = new URL(`${API_BASE}/api/catalog/list`)
  if (params?.pinned_only) url.searchParams.set('pinned_only', 'true')
  if (params?.category) url.searchParams.set('category', params.category)
  if (params?.sort_by) url.searchParams.set('sort_by', params.sort_by)
  const res = await fetch(url.toString())
  return handleResponse<CatalogListResponse>(res)
}

export async function searchCatalog(q: string, category?: string) {
  const url = new URL(`${API_BASE}/api/catalog/search`)
  url.searchParams.set('q', q)
  if (category) url.searchParams.set('category', category)
  const res = await fetch(url.toString())
  return handleResponse<CatalogListResponse>(res)
}

export async function pinDocument(docId: number, pinned: boolean) {
  const res = await fetch(`${API_BASE}/api/catalog/pin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id: docId, pinned }),
  })
  return handleResponse(res)
}

export async function getCatalogStats(): Promise<CatalogStats> {
  const res = await fetch(`${API_BASE}/api/catalog/stats`)
  return handleResponse<CatalogStats>(res)
}

export async function deleteDocument(docId: number) {
  const res = await fetch(`${API_BASE}/api/catalog/${docId}`, { method: 'DELETE' })
  return handleResponse(res)
}

export async function queryMultiDoc(body: {
  doc_ids: number[]
  question: string
  mode: MultiDocMode
}) {
  const res = await fetch(`${API_BASE}/api/multi-doc/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return handleResponse<MultiDocResponse>(res)
}
