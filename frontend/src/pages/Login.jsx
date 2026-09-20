import React, { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Leaf, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { errorMessage, fieldErrors } from "../lib/api";
import { ErrorSummary, FieldError, describedBy } from "../components/FormErrors";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function Login() {
  const { user, loading, login, register } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", identifier: "", email: "", mobile: "", password: "" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [fields, setFields] = useState({});
  const redirect = new URLSearchParams(location.search).get("redirect")
    || location.state?.from
    || "/";

  if (!loading && user) {
    return <Navigate to={redirect} replace />;
  }

  const updateField = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    // Clear a field's complaint as soon as it is being corrected.
    setFields((current) => {
      if (!current[name]) return current;
      const next = { ...current };
      delete next[name];
      return next;
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const problems = findProblems();
    if (Object.keys(problems).length > 0) {
      setError("");
      setFields(problems);
      return;
    }

    setSubmitting(true);
    setError("");
    setFields({});
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
      setError(errorMessage(requestError, "Authentication failed. Please try again."));
      setFields(fieldErrors(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const switchMode = () => {
    setMode((current) => current === "login" ? "register" : "login");
    setError("");
    setFields({});
  };

  /**
   * Catch what can be judged without asking the server.
   *
   * Only emptiness and length are checked here. Whether a mobile number is a
   * real Indian one is the API's rule, and repeating it in the browser would
   * mean two places to keep in step.
   */
  const findProblems = () => {
    const problems = {};
    if (mode === "register") {
      if (form.name.trim().length < 2) {
        problems.name = "Enter your name, using at least 2 characters.";
      }
      if (!form.mobile.trim()) {
        problems.mobile = "Enter your mobile number.";
      }
      if (form.password.length < 8) {
        problems.password = "Use a password of at least 8 characters.";
      }
    } else {
      if (!form.identifier.trim()) {
        problems.identifier = "Enter your mobile number or email.";
      }
      if (!form.password) {
        problems.password = "Enter your password.";
      }
    }
    return problems;
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

        <form onSubmit={handleSubmit} className="mt-8 space-y-5" data-testid="auth-form" noValidate>
          <ErrorSummary message={error} fields={fields} />

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
                {...describedBy("name", { error: Boolean(fields.name) })}
              />
              <FieldError name="name">{fields.name}</FieldError>
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
                {...describedBy("identifier", { error: Boolean(fields.identifier) })}
              />
              <FieldError name="identifier">{fields.identifier}</FieldError>
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
                  {...describedBy("mobile", { hint: true, error: Boolean(fields.mobile) })}
                />
                <p id="mobile-hint" className="text-xs text-[#64748B]">
                  We use this to reach you about your orders.
                </p>
                <FieldError name="mobile">{fields.mobile}</FieldError>
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={updateField}
                  autoComplete="email"
                  className="h-11"
                  data-testid="auth-email-optional-input"
                  {...describedBy("email", { hint: true, error: Boolean(fields.email) })}
                />
                <p id="email-hint" className="text-xs text-[#64748B]">
                  You can skip this, or add one for receipts by email.
                </p>
                <FieldError name="email">{fields.email}</FieldError>
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
              {...describedBy("password", {
                hint: mode === "register",
                error: Boolean(fields.password),
              })}
            />
            {mode === "register" && (
              <p id="password-hint" className="text-xs text-[#64748B]">
                Use at least 8 characters.
              </p>
            )}
            <FieldError name="password">{fields.password}</FieldError>
          </div>

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
