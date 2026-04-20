import React from "react";
import { useAuth } from "../context/AuthContext";
import { Navigate, useLocation } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Leaf, ShieldCheck } from "lucide-react";

export default function Login() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (!loading && user) {
    const redirect = new URLSearchParams(location.search).get("redirect") || "/";
    return <Navigate to={redirect} replace />;
  }

  const handleGoogleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + (new URLSearchParams(location.search).get("redirect") || "/");
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="max-w-md mx-auto px-6 py-16" data-testid="login-page">
      <div className="rounded-3xl border border-[var(--nayara-border)] bg-white p-10 text-center">
        <div className="w-14 h-14 rounded-full mx-auto flex items-center justify-center text-white font-bold text-2xl" style={{ background: "var(--nayara-primary)" }}>N</div>
        <h1 className="font-heading text-3xl font-medium mt-5 tracking-tight">Welcome to Nayara</h1>
        <p className="text-[#64748B] mt-2">Sign in to save your wishlist, track orders and check out faster.</p>
        <Button onClick={handleGoogleLogin} className="mt-8 w-full h-12 bg-[var(--nayara-primary)] hover:bg-[var(--nayara-primary-hover)] rounded-full" data-testid="google-login-btn">
          <svg className="w-5 h-5 mr-2" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C12.955 4 4 12.955 4 24s8.955 20 20 20s20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"/><path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C16.318 4 9.656 8.337 6.306 14.691z"/><path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0 1 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"/><path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"/></svg>
          Continue with Google
        </Button>
        <div className="mt-6 text-xs text-[#64748B] flex items-center justify-center gap-3">
          <span className="flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Secure</span>
          <span>·</span>
          <span className="flex items-center gap-1"><Leaf className="w-3 h-3" /> No spam</span>
        </div>
      </div>
    </div>
  );
}
