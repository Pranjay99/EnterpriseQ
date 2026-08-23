import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const url = process.env.NEXT_PUBLIC_SUPABASE_URL
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

/**
 * Browser Supabase client. `null` when the env vars are not configured,
 * in which case the app runs without authentication (local dev only).
 */
export const supabase: SupabaseClient | null =
  url && anonKey ? createClient(url, anonKey) : null
