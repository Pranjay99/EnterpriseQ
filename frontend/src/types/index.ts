export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  chartJson?: string
  sqlQuery?: string
  sources?: string[]
  timestamp: Date
}

export interface UploadResponse {
  filename: string
  rows?: number
  columns?: string[]
  column_types?: Record<string, string>
  size_mb?: number
  table_name?: string
  chunks?: number
  file_type: 'data' | 'document'
  doc_id?: number
  category?: string
  tags?: string[]
  summary?: string
  message: string
}

export interface CatalogItem {
  id: number
  filename: string
  file_type: string
  category: string
  tags: string[]
  summary: string
  upload_date: string
  last_accessed?: string
  query_count: number
  is_pinned: boolean
  vector_collection: string
}

export interface CatalogListResponse {
  documents: CatalogItem[]
  total: number
}

export interface MultiDocResponse {
  answer: string
  sources: string[]
  mode: string
}

export interface CatalogStats {
  total_documents: number
  total_queries: number
  most_queried?: CatalogItem | null
  category_breakdown: Record<string, number>
  pinned_count: number
}

export type QueryMode = 'sql' | 'dataframe' | 'rag' | 'general' | 'auto'
export type MultiDocMode = 'synthesize' | 'compare' | 'per_doc'

export interface ChatRequest {
  session_id: string
  question: string
  mode: QueryMode
  doc_id?: number | null
  doc_ids?: number[] | null
  multi_doc_mode?: MultiDocMode
}

export interface ChatResponse {
  answer: string
  chart_json?: string
  sql_query?: string
  sources?: string[]
}
