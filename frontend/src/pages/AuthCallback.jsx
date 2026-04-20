import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash;
    const params = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);
    const session_id = params.get("session_id");
    if (!session_id) { navigate("/login"); return; }

    (async () => {
      try {
        const { data } = await api.post("/auth/session", { session_id });
        setUser(data.user);
        const target = window.location.pathname || "/";
        window.history.replaceState(null, "", target);
        navigate(target === "/" ? "/" : target, { replace: true, state: { user: data.user } });
      } catch (e) {
        setError("Could not sign you in. Please try again.");
        setTimeout(() => navigate("/login"), 2000);
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center" data-testid="auth-callback">
      <div className="text-center">
        <div className="w-10 h-10 border-4 border-[var(--nayara-primary)] border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="mt-4 text-[#64748B]">{error || "Signing you in..."}</p>
      </div>
    </div>
  );
}
