import { createContext, useContext, useEffect, useState, type ReactNode, useCallback } from "react";
import { supabase } from "../lib/supabase";
import type { Session, User } from "@supabase/supabase-js";

interface AuthContextType {
  session: Session | null;
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  loginWithPassword: (email: string, password: string) => Promise<void>;
  sendOtp: (email: string) => Promise<void>;
  verifyOtp: (email: string, token: string) => Promise<void>;
  sendPhoneOtp: (phone: string) => Promise<void>;
  verifyPhoneOtp: (phone: string, token: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setUser(s?.user ?? null);
      setLoading(false);
    });

    // Listen for auth changes (login, logout, token refresh). The subscription
    // must be re-created on every mount — under React StrictMode the first
    // mount's cleanup runs before the second mount, so a run-once guard here
    // would leave the app with no active listener and logins would not
    // navigate until a manual reload.
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      setUser(s?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const loginWithPassword = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }, []);

  const sendOtp = useCallback(async (email: string) => {
    const { error } = await supabase.auth.signInWithOtp({ email });
    if (error) throw error;
  }, []);

  const verifyOtp = useCallback(async (email: string, token: string) => {
    const { error } = await supabase.auth.verifyOtp({ email, token, type: "email" });
    if (error) throw error;
  }, []);

  const sendPhoneOtp = useCallback(async (phone: string) => {
    const { error } = await supabase.auth.signInWithOtp({ phone });
    if (error) throw error;
  }, []);

  const verifyPhoneOtp = useCallback(async (phone: string, token: string) => {
    const { error } = await supabase.auth.verifyOtp({ phone, token, type: "sms" });
    if (error) throw error;
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email);
    if (error) throw error;
  }, []);

  const logout = useCallback(async () => {
    await supabase.auth.signOut();
    setSession(null);
    setUser(null);
  }, []);

  // Don't render children until we know the auth state
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0D1B2A] flex items-center justify-center text-[#E8ECF1]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#00895E] mx-auto mb-4"></div>
          <p className="text-[#E8ECF1]/60">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{
      session, user, loading, isAuthenticated: !!session,
      loginWithPassword, sendOtp, verifyOtp, sendPhoneOtp, verifyPhoneOtp,
      signup, resetPassword, logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
