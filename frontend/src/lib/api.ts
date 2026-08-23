import type {
  ChatRequest,
  ChatResponse,
  CatalogListResponse,
  CatalogStats,
  MultiDocMode,
  MultiDocResponse,
  UploadResponse,
} from '@/types'

import { supabase } from './supabase'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Authorization header with the Supabase access token.
 * Empty when auth is not configured (local dev).
 */
async function authHeaders(): Promise<Record<string, string>> {
  if (!supabase) return {}
  const { data } = await supabase.auth.getSession()
  return data.session
    ? { Authorization: `Bearer ${data.session.access_token}` }
    : {}
}

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
    headers: await authHeaders(),
    body: formData,
  })
  return handleResponse<UploadResponse>(res)
}

export async function clearSession(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/upload/${sessionId}`, {
    method: 'DELETE',
    headers: await authHeaders(),
  })
  return handleResponse<{ message: string }>(res)
}

export async function sendChat(body: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify(body),
  })
  return handleResponse<ChatResponse>(res)
}

export async function uploadToCatalog(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/catalog/upload`, {
    method: 'POST',
    headers: await authHeaders(),
    body: formData,
  })
  return handleResponse<UploadResponse>(res)
}

export async function addTableToCatalog(
  sessionId: string,
  tableName: string,
  filename: string
): Promise<UploadResponse> {
  const res = await fetch(`${API_BASE}/api/catalog/add-table`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify({ session_id: sessionId, table_name: tableName, filename }),
  })
  return handleResponse<UploadResponse>(res)
}

export async function loadCatalogDoc(docId: number, sessionId: string): Promise<UploadResponse> {
  const res = await fetch(`${API_BASE}/api/catalog/${docId}/load/${sessionId}`, {
    method: 'POST',
    headers: await authHeaders(),
  })
  return handleResponse<UploadResponse>(res)
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
  const res = await fetch(url.toString(), { headers: await authHeaders() })
  return handleResponse<CatalogListResponse>(res)
}

export async function searchCatalog(q: string, category?: string) {
  const url = new URL(`${API_BASE}/api/catalog/search`)
  url.searchParams.set('q', q)
  if (category) url.searchParams.set('category', category)
  const res = await fetch(url.toString(), { headers: await authHeaders() })
  return handleResponse<CatalogListResponse>(res)
}

export async function pinDocument(docId: number, pinned: boolean) {
  const res = await fetch(`${API_BASE}/api/catalog/pin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify({ doc_id: docId, pinned }),
  })
  return handleResponse(res)
}

export async function getCatalogStats(): Promise<CatalogStats> {
  const res = await fetch(`${API_BASE}/api/catalog/stats`, { headers: await authHeaders() })
  return handleResponse<CatalogStats>(res)
}

export async function deleteDocument(docId: number) {
  const res = await fetch(`${API_BASE}/api/catalog/${docId}`, {
    method: 'DELETE',
    headers: await authHeaders(),
  })
  return handleResponse(res)
}

export async function queryMultiDoc(body: {
  doc_ids: number[]
  question: string
  mode: MultiDocMode
}) {
  const res = await fetch(`${API_BASE}/api/multi-doc/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify(body),
  })
  return handleResponse<MultiDocResponse>(res)
}
