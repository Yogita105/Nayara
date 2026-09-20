import React from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { Button } from "./ui/button";

/**
 * Tells someone what is happening when a screen has nothing to show yet.
 *
 * A blank area is ambiguous: it could be loading, empty, or broken. Saying
 * which, and offering a way forward, avoids the customer guessing.
 */
export function LoadingPanel({ label = "Loading...", testId = "loading-panel" }) {
  return (
    <div
      className="flex flex-col items-center justify-center py-16 text-[#64748B]"
      role="status"
      aria-live="polite"
      data-testid={testId}
    >
      <Loader2 className="w-7 h-7 animate-spin mb-3" aria-hidden="true" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function ErrorPanel({ message, onRetry, testId = "error-panel" }) {
  return (
    <div
      className="text-center py-14 rounded-2xl border border-[var(--nayara-border)] bg-white"
      role="alert"
      data-testid={testId}
    >
      <p className="text-[#0F172A] font-medium">We could not load this</p>
      <p className="text-sm text-[#64748B] mt-2 px-6">{message}</p>
      {onRetry && (
        <Button
          type="button"
          variant="outline"
          onClick={onRetry}
          className="mt-5 rounded-full"
          data-testid="retry-btn"
        >
          <RefreshCw className="w-4 h-4 mr-2" aria-hidden="true" /> Try again
        </Button>
      )}
    </div>
  );
}

export function EmptyPanel({ icon: Icon, title, message, action, testId = "empty-panel" }) {  return (
    <div
      className="text-center py-16 rounded-2xl border border-[var(--nayara-border)] bg-white"
      data-testid={testId}
    >
      {Icon && <Icon className="w-14 h-14 mx-auto text-[#64748B] mb-4" aria-hidden="true" />}
      {title && <p className="font-medium text-[#0F172A]">{title}</p>}
      {message && <p className="text-[#64748B] mt-1">{message}</p>}
      {action}
    </div>
  );
}

/**
 * Explains an admin table that has no rows, without breaking the table layout.
 */
export function TableStateRow({ columns, loading, error, onRetry, emptyMessage }) {
  if (!loading && !error && !emptyMessage) return null;
  return (
    <tr>
      <td colSpan={columns} className="px-4 py-10 text-center text-[#64748B]" data-testid="table-state">
        {loading ? (
          <span className="inline-flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> Loading...
          </span>
        ) : error ? (
          <span className="inline-flex flex-wrap items-center justify-center gap-3">
            <span className="text-[#0F172A]">{error}</span>
            {onRetry && (
              <Button type="button" variant="outline" size="sm" onClick={onRetry} className="rounded-full" data-testid="table-retry-btn">
                <RefreshCw className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" /> Try again
              </Button>
            )}
          </span>
        ) : (
          emptyMessage
        )}
      </td>
    </tr>
  );
}
