'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { Cpu, LogIn, UserRound } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'

interface AuthContextValue {
  user: User | null
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  signOut: async () => {},
})

export const useAuth = () => useContext(AuthContext)

function LoginScreen() {
  const [error, setError] = useState<string | null>(null)
  const [guestLoading, setGuestLoading] = useState(false)

  const signInWithGoogle = async () => {
    if (!supabase) return
    setError(null)
    const { error: err } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
    if (err) setError(err.message)
  }

  const signInAsGuest = async () => {
    if (!supabase) return
    setError(null)
    setGuestLoading(true)
    const { error: err } = await supabase.auth.signInAnonymously()
    setGuestLoading(false)
    if (err) {
      setError(
        err.message.toLowerCase().includes('anonymous')
          ? 'Guest access is not enabled yet. Enable "Anonymous sign-ins" in the Supabase dashboard (Authentication → Sign In / Up).'
          : err.message
      )
    }
  }

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <div className="flex w-full max-w-sm flex-col items-center gap-6 rounded-xl border border-border bg-card p-10">
        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary">
          <Cpu className="h-7 w-7 text-primary-foreground" />
        </div>
        <div className="text-center">
          <h1 className="text-xl font-semibold">Enterprise Q</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Sign in to access your data assistant
          </p>
        </div>
        <div className="flex w-full flex-col gap-3">
          <Button onClick={signInWithGoogle} className="w-full gap-2">
            <LogIn className="h-4 w-4" />
            Continue with Google
          </Button>
          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">or</span>
            <div className="h-px flex-1 bg-border" />
          </div>
          <Button
            onClick={signInAsGuest}
            variant="outline"
            className="w-full gap-2"
            disabled={guestLoading}
          >
            <UserRound className="h-4 w-4" />
            {guestLoading ? 'Starting guest session…' : 'Continue as guest'}
          </Button>
          <p className="text-center text-[11px] text-muted-foreground">
            Guest data is tied to this browser and is lost when you sign out.
          </p>
        </div>
        {error && (
          <p className="text-center text-xs text-destructive">{error}</p>
        )}
      </div>
    </div>
  )
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(!!supabase)

  useEffect(() => {
    if (!supabase) return
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession)
    })
    return () => sub.subscription.unsubscribe()
  }, [])

  // Auth not configured — run open (local development only).
  if (!supabase) {
    return (
      <AuthContext.Provider value={{ user: null, signOut: async () => {} }}>
        {children}
      </AuthContext.Provider>
    )
  }

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!session) return <LoginScreen />

  return (
    <AuthContext.Provider
      value={{
        user: session.user,
        signOut: async () => {
          await supabase?.auth.signOut()
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
