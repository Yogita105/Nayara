import React, { useEffect, useRef } from "react";
import { AlertCircle } from "lucide-react";

/**
 * Tell someone what went wrong in a way they cannot miss.
 *
 * A message placed beside the submit button is only found by a screen reader
 * once the whole form has been read past. This instead announces itself, takes
 * focus, and links to the field that needs correcting, so the next press of
 * Tab lands where the work is.
 */
export function ErrorSummary({ message, fields = {}, testId = "form-error-summary" }) {
  const container = useRef(null);
  const entries = Object.entries(fields);
  const hasProblem = Boolean(message) || entries.length > 0;
  const signature = `${message || ""}|${entries.map(([k]) => k).join(",")}`;

  useEffect(() => {
    if (hasProblem) container.current?.focus();
  }, [hasProblem, signature]);

  if (!hasProblem) return null;

  // When the general message only repeats a field's own complaint, saying it
  // twice makes a screen reader read the same sentence twice over. The API
  // prefixes its sentence with the field's name -- "Phone: Enter a number we
  // can ring" -- so the two are rarely identical, only ever one inside the
  // other.
  const alreadyListed = entries.some(
    ([, text]) => text && (text === message || message?.endsWith(text))
  );
  const heading = message && !alreadyListed
    ? message
    : "Please correct the following before continuing.";

  return (
    <div
      ref={container}
      tabIndex={-1}
      role="alert"
      className="rounded-xl border border-red-200 bg-red-50 p-4 outline-none focus:ring-2 focus:ring-red-400"
      data-testid={testId}
    >
      <p className="flex items-start gap-2 text-sm font-medium text-red-800">
        <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />
        <span>{entries.length === 0 ? message : heading}</span>
      </p>
      {entries.length > 0 && (
        <ul className="mt-2 ml-6 list-disc space-y-1 text-sm text-red-800">
          {entries.map(([field, text]) => (
            <li key={field}>
              {/* A plain fragment link moves focus to the field natively. */}
              <a href={`#${field}`} className="underline hover:no-underline">
                {text}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * The message for one field, named so the input can point at it.
 */
export function FieldError({ name, children }) {
  if (!children) return null;
  return (
    <p id={`${name}-error`} className="text-sm text-red-600" data-testid={`${name}-error`}>
      {children}
    </p>
  );
}

/**
 * The attributes an input needs so its hint and error are read with it.
 *
 * Without these the message is on screen but unconnected: someone using a
 * screen reader hears the label and nothing else.
 */
export function describedBy(name, { hint = false, error = false } = {}) {
  const ids = [];
  if (hint) ids.push(`${name}-hint`);
  if (error) ids.push(`${name}-error`);
  return {
    "aria-invalid": error || undefined,
    "aria-describedby": ids.length ? ids.join(" ") : undefined,
  };
}
