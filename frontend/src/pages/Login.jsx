import React, { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Leaf, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function Login() {
  const { user, loading, login, register } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", identifier: "", email: "", mobile: "", password: "" });  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const redirect = new URLSearchParams(location.search).get("redirect")
    || location.state?.from
    || "/";

  if (!loading && user) {
    return <Navigate to={redirect} replace />;
  }

  const updateField = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      if (mode === "register") {
        await register({
          name: form.name,
          mobile: form.mobile,
          password: form.password,
          // Sent only when given, since an address is optional.
          ...(form.email.trim() ? { email: form.email.trim() } : {}),
        });
      } else {
        await login({ identifier: form.identifier, password: form.password });
      }
      navigate(redirect, { replace: true });
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail
          || "Authentication failed. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  const switchMode = () => {
    setMode((current) => current === "login" ? "register" : "login");
    setError("");
  };

  return (
    <div className="max-w-md mx-auto px-6 py-16" data-testid="login-page">
      <div className="rounded-3xl border border-[var(--nayara-border)] bg-white p-10">
        <div className="w-14 h-14 rounded-full mx-auto flex items-center justify-center text-white font-bold text-2xl" style={{ background: "var(--nayara-primary)" }}>N</div>
        <div className="text-center">
          <h1 className="font-heading text-3xl font-medium mt-5 tracking-tight">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h1>
          <p className="text-[#64748B] mt-2">
            {mode === "login"
              ? "Sign in to view your orders and saved products."
              : "Join Nayara for a faster, more personal shopping experience."}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5" data-testid="auth-form">
          {mode === "register" && (
            <div className="space-y-2">
              <Label htmlFor="name" required>Name</Label>
              <Input
                id="name"
                name="name"
                value={form.name}
                onChange={updateField}
                autoComplete="name"
                minLength={2}
                maxLength={100}
                required
                className="h-11"
                data-testid="auth-name-input"
              />
            </div>
          )}
          {mode === "login" ? (
            <div className="space-y-2">
              <Label htmlFor="identifier" required>Mobile number or email</Label>
              <Input
                id="identifier"
                name="identifier"
                type="text"
                value={form.identifier}
                onChange={updateField}
                autoComplete="username"
                placeholder="10-digit mobile number or email"
                required
                className="h-11"
                data-testid="auth-email-input"
              />
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="mobile" required>Mobile number</Label>
                <Input
                  id="mobile"
                  name="mobile"
                  type="tel"
                  inputMode="numeric"
                  value={form.mobile}
                  onChange={updateField}
                  autoComplete="tel"
                  placeholder="10-digit Indian mobile number"
                  minLength={10}
                  maxLength={20}
                  required
                  className="h-11"
                  data-testid="auth-mobile-input"
                />
                <p className="text-xs text-[#64748B]">
                  We use this to reach you about your orders.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email (optional)</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={updateField}
                  autoComplete="email"
                  className="h-11"
                  data-testid="auth-email-optional-input"
                />
                <p className="text-xs text-[#64748B]">
                  Add one if you would like receipts by email.
                </p>
              </div>
            </>
          )}
          <div className="space-y-2">
            <Label htmlFor="password" required>Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              value={form.password}
              onChange={updateField}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={mode === "register" ? 8 : 1}
              maxLength={128}
              required
              className="h-11"
              data-testid="auth-password-input"
            />
            {mode === "register" && (
              <p className="text-xs text-[#64748B]">Use at least 8 characters.</p>
            )}
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-600" data-testid="auth-error">
              {error}
            </p>
          )}

          <Button
            type="submit"
            disabled={submitting}
            className="w-full h-12 bg-[var(--nayara-primary)] hover:bg-[var(--nayara-primary-hover)] rounded-full"
            data-testid="auth-submit-btn"
          >
            {submitting
              ? "Please wait..."
              : mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <p className="mt-6 text-sm text-center text-[#64748B]">
          {mode === "login" ? "New to Nayara?" : "Already have an account?"}{" "}
          <button
            type="button"
            onClick={switchMode}
            className="font-medium text-[var(--nayara-primary)] hover:underline"
            data-testid="auth-mode-toggle"
          >
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </p>
        <div className="mt-6 text-xs text-[#64748B] flex items-center justify-center gap-3">
          <span className="flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Secure</span>
          <span>·</span>
          <span className="flex items-center gap-1"><Leaf className="w-3 h-3" /> No spam</span>
        </div>
      </div>
    </div>
  );
}
