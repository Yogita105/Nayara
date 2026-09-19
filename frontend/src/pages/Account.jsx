import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound, LogOut, ShieldCheck, UserRound } from "lucide-react";
import { toast } from "sonner";
import { api, setCsrfToken } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

const EMPTY_FORM = { current_password: "", new_password: "", confirm_password: "" };

export default function Account() {
  const { user, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState("");

  const [profile, setProfile] = useState({
    name: user?.name || "",
    mobile: user?.mobile || "",
  });
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState("");
  const missingMobile = !user?.mobile;

  const updateProfileField = (event) =>
    setProfile((current) => ({ ...current, [event.target.name]: event.target.value }));

  const saveProfile = async (event) => {
    event.preventDefault();
    setProfileError("");
    setSavingProfile(true);
    try {
      const { data } = await api.put("/auth/profile", profile);
      setProfile({ name: data.name, mobile: data.mobile || "" });
      await checkAuth();
      toast.success("Details saved.");
    } catch (requestError) {
      setProfileError(
        requestError.response?.data?.detail || "Could not save your details."
      );
    } finally {
      setSavingProfile(false);
    }
  };

  const updateField = (event) =>
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));

  const changePassword = async (event) => {
    event.preventDefault();
    setError("");

    if (form.new_password !== form.confirm_password) {
      setError("The new passwords do not match.");
      return;
    }

    setSaving(true);
    try {
      const { data } = await api.post("/auth/password", {
        current_password: form.current_password,
        new_password: form.new_password,
      });
      setForm(EMPTY_FORM);
      toast.success(
        data.other_sessions_ended
          ? `Password updated. Signed out of ${data.other_sessions_ended} other device(s).`
          : "Password updated."
      );
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail || "Could not update the password."
      );
    } finally {
      setSaving(false);
    }
  };

  const signOutEverywhere = async () => {
    setSigningOut(true);
    try {
      await api.post("/auth/logout-all");
      setCsrfToken(null);
      await checkAuth();
      toast.success("Signed out of all devices.");
      navigate("/login");
    } catch {
      toast.error("Could not sign out of all devices.");
    } finally {
      setSigningOut(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-10" data-testid="account-page">
      <h1 className="font-heading text-2xl md:text-3xl font-medium tracking-tight mb-2">
        Account
      </h1>
      <p className="text-[#64748B] mb-8">{user?.email}</p>

      <section className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 mb-6">
        <h2 className="font-heading text-lg font-semibold flex items-center gap-2">
          <UserRound className="w-4 h-4" /> Your details
        </h2>
        <p className="text-sm text-[#64748B] mt-1 mb-5">
          {missingMobile
            ? "Add a mobile number so we can reach you about your orders."
            : "Keep these up to date so we can reach you about your orders."}
        </p>

        <form onSubmit={saveProfile} className="space-y-4" data-testid="profile-form">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              name="name"
              value={profile.name}
              onChange={updateProfileField}
              autoComplete="name"
              minLength={2}
              maxLength={100}
              required
              className="h-11"
              data-testid="profile-name-input"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="profile-email">Email</Label>
            <Input
              id="profile-email"
              value={user?.email || ""}
              readOnly
              disabled
              className="h-11 bg-[#F8FAFC]"
              data-testid="profile-email-input"
            />
            <p className="text-xs text-[#64748B]">
              Your email identifies the account and cannot be changed here.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="mobile">Mobile number</Label>
            <Input
              id="mobile"
              name="mobile"
              type="tel"
              inputMode="numeric"
              value={profile.mobile}
              onChange={updateProfileField}
              autoComplete="tel"
              placeholder="10-digit Indian mobile number"
              minLength={10}
              maxLength={20}
              required
              className="h-11"
              data-testid="profile-mobile-input"
            />
          </div>

          {profileError && (
            <p role="alert" className="text-sm text-red-600" data-testid="profile-error">
              {profileError}
            </p>
          )}

          <Button
            type="submit"
            disabled={savingProfile}
            className="h-11 rounded-full bg-[var(--nayara-primary)] hover:bg-[var(--nayara-primary-hover)]"
            data-testid="profile-submit-btn"
          >
            {savingProfile ? "Saving..." : "Save details"}
          </Button>
        </form>
      </section>

      <section className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 mb-6">
        <h2 className="font-heading text-lg font-semibold flex items-center gap-2">
          <KeyRound className="w-4 h-4" /> Change password
        </h2>
        <p className="text-sm text-[#64748B] mt-1 mb-5">
          Changing your password signs you out everywhere else.
        </p>

        <form onSubmit={changePassword} className="space-y-4" data-testid="password-form">
          <div className="space-y-2">
            <Label htmlFor="current_password">Current password</Label>
            <Input
              id="current_password"
              name="current_password"
              type="password"
              value={form.current_password}
              onChange={updateField}
              autoComplete="current-password"
              required
              className="h-11"
              data-testid="current-password-input"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new_password">New password</Label>
            <Input
              id="new_password"
              name="new_password"
              type="password"
              value={form.new_password}
              onChange={updateField}
              autoComplete="new-password"
              minLength={8}
              required
              className="h-11"
              data-testid="new-password-input"
            />
            <p className="text-xs text-[#64748B]">Use at least 8 characters.</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm_password">Confirm new password</Label>
            <Input
              id="confirm_password"
              name="confirm_password"
              type="password"
              value={form.confirm_password}
              onChange={updateField}
              autoComplete="new-password"
              minLength={8}
              required
              className="h-11"
              data-testid="confirm-password-input"
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-600" data-testid="password-error">
              {error}
            </p>
          )}

          <Button
            type="submit"
            disabled={saving}
            className="h-11 rounded-full bg-[var(--nayara-primary)] hover:bg-[var(--nayara-primary-hover)]"
            data-testid="password-submit-btn"
          >
            {saving ? "Updating..." : "Update password"}
          </Button>
        </form>
      </section>

      <section className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
        <h2 className="font-heading text-lg font-semibold flex items-center gap-2">
          <ShieldCheck className="w-4 h-4" /> Signed-in devices
        </h2>
        <p className="text-sm text-[#64748B] mt-1 mb-5">
          If you have used a shared or lost device, sign out everywhere. You will
          need to sign in again on this one.
        </p>
        <Button
          type="button"
          variant="outline"
          onClick={signOutEverywhere}
          disabled={signingOut}
          className="h-11 rounded-full"
          data-testid="logout-all-btn"
        >
          <LogOut className="w-4 h-4 mr-2" />
          {signingOut ? "Signing out..." : "Sign out of all devices"}
        </Button>
      </section>
    </div>
  );
}
