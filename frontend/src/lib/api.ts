import type { ChatRequest, ChatResponse, CatalogStats, MultiDocMode } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function uploadFile(sessionId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/upload/${sessionId}`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function clearSession(sessionId: string) {
  await fetch(`${API_BASE}/api/upload/${sessionId}`, { method: 'DELETE' })
}

export async function sendChat(body: ChatRequest) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<ChatResponse>
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
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function searchCatalog(q: string, category?: string) {
  const url = new URL(`${API_BASE}/api/catalog/search`)
  url.searchParams.set('q', q)
  if (category) url.searchParams.set('category', category)
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function pinDocument(docId: number, pinned: boolean) {
  const res = await fetch(`${API_BASE}/api/catalog/pin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id: docId, pinned }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getCatalogStats() {
  const res = await fetch(`${API_BASE}/api/catalog/stats`)
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<CatalogStats>
}

export async function deleteDocument(docId: number) {
  const res = await fetch(`${API_BASE}/api/catalog/${docId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
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
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
