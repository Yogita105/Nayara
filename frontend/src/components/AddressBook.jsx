import React, { useState } from "react";
import { MapPin, Pencil, Plus, Star, Trash2 } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import AddressFields from "./AddressFields";
import { ErrorSummary } from "./FormErrors";
import { EMPTY_ADDRESS, deliveryPartOf, findProblems, oneLine } from "../lib/addresses";
import { fieldErrors } from "../lib/api";

const BLANK = { ...EMPTY_ADDRESS, label: "", is_default: false };

/**
 * The saved addresses, and the form for adding or changing one.
 *
 * Only one form is on screen at a time: the fields carry ids matching their
 * names so the error summary can link to them, and two copies would make
 * those links ambiguous.
 */
export default function AddressBook({ book }) {
  const { addresses, loading, error, save, update, remove } = book;
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState(BLANK);
  const [fields, setFields] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  const startAdding = () => {
    setDraft({ ...BLANK, is_default: addresses.length === 0 });
    setEditing("new");
    setFields({});
    setFormError("");
  };

  const startEditing = (address) => {
    setDraft({ ...BLANK, ...address });
    setEditing(address.address_id);
    setFields({});
    setFormError("");
  };

  const stopEditing = () => {
    setEditing(null);
    setFields({});
    setFormError("");
  };

  const updateField = (name) => (event) => {
    const { value } = event.target;
    setDraft((current) => ({ ...current, [name]: value }));
    setFields((current) => {
      if (!current[name]) return current;
      const next = { ...current };
      delete next[name];
      return next;
    });
  };

  const submit = async (event) => {
    event.preventDefault();
    const problems = findProblems(draft);
    if (Object.keys(problems).length > 0) {
      setFormError("");
      setFields(problems);
      return;
    }

    setBusy(true);
    setFields({});
    setFormError("");
    const payload = {
      ...deliveryPartOf(draft),
      label: draft.label || "",
      is_default: Boolean(draft.is_default),
    };
    const result =
      editing === "new" ? await save(payload) : await update(editing, payload);
    setBusy(false);

    if (result.ok) {
      stopEditing();
      return;
    }
    setFormError(result.message);
    setFields(fieldErrors(result.failure));
  };

  const confirmRemove = async (address) => {
    const name = address.label || oneLine(address);
    if (!window.confirm(`Remove ${name} from your saved addresses?`)) return;
    const result = await remove(address.address_id);
    if (!result.ok) setFormError(result.message);
  };

  return (
    <section
      className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 mb-6"
      data-testid="address-book"
    >
      <h2 className="font-heading text-lg font-semibold flex items-center gap-2">
        <MapPin className="w-4 h-4" /> Delivery addresses
      </h2>
      <p className="text-sm text-[#64748B] mt-1 mb-5">
        Saved addresses are offered at checkout, so you do not have to type one
        again. Past orders keep the address they were sent to.
      </p>

      {loading ? (
        <p className="text-sm text-[#64748B]" data-testid="address-loading">
          Loading your addresses...
        </p>
      ) : (
        <>
          {error && (
            <p role="alert" className="text-sm text-red-600 mb-4" data-testid="address-error">
              {error}
            </p>
          )}

          {addresses.length === 0 && editing !== "new" && (
            <p className="text-sm text-[#64748B] mb-4" data-testid="address-none">
              You have not saved an address yet.
            </p>
          )}

          <ul className="space-y-3 mb-5">
            {addresses.map((address) => (
              <li
                key={address.address_id}
                className="rounded-xl border border-[var(--nayara-border)] p-4"
                data-testid={`address-${address.address_id}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium">{address.label || address.full_name}</span>
                      {address.is_default && (
                        <span
                          className="text-[11px] font-semibold px-2 py-0.5 rounded-full badge-soft flex items-center gap-1"
                          data-testid={`address-usual-${address.address_id}`}
                        >
                          <Star className="w-3 h-3" /> Usual
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-[#64748B] mt-1">{address.full_name}</p>
                    <p className="text-sm text-[#64748B]">{oneLine(address)}</p>
                    <p className="text-sm text-[#64748B]">{address.phone}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => startEditing(address)}
                      className="text-sm px-3 py-1.5 rounded-md border border-[var(--nayara-border)] hover:bg-[#FBEEE4] flex items-center gap-1"
                      data-testid={`address-edit-${address.address_id}`}
                    >
                      <Pencil className="w-3.5 h-3.5" /> Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => confirmRemove(address)}
                      className="text-sm px-3 py-1.5 rounded-md border border-[var(--nayara-border)] hover:bg-red-50 text-red-600 flex items-center gap-1"
                      data-testid={`address-remove-${address.address_id}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Remove
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>

          {editing ? (
            <form onSubmit={submit} className="space-y-4" data-testid="address-form" noValidate>
              <ErrorSummary message={formError} fields={fields} />

              <div className="space-y-2">
                <Label htmlFor="label" className="text-xs font-bold uppercase tracking-[0.15em]">
                  Name this address
                </Label>
                <Input
                  id="label"
                  value={draft.label}
                  onChange={updateField("label")}
                  maxLength={30}
                  placeholder="Home, Office, Mum's"
                  data-testid="addr-label"
                />
              </div>

              <AddressFields address={draft} onChange={updateField} fields={fields} />

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={Boolean(draft.is_default)}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, is_default: event.target.checked }))
                  }
                  data-testid="addr-default"
                />
                Use this address by default
              </label>

              <div className="flex gap-3">
                <Button
                  type="submit"
                  disabled={busy}
                  className="h-11 rounded-full bg-[var(--nayara-primary)] hover:bg-[var(--nayara-primary-hover)]"
                  data-testid="address-save"
                >
                  {busy ? "Saving..." : "Save address"}
                </Button>
                <button
                  type="button"
                  onClick={stopEditing}
                  className="text-sm px-4 py-2 rounded-full border border-[var(--nayara-border)]"
                  data-testid="address-cancel"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <button
              type="button"
              onClick={startAdding}
              className="text-sm px-4 py-2 rounded-full border border-[var(--nayara-border)] hover:bg-[#FBEEE4] flex items-center gap-1"
              data-testid="address-add"
            >
              <Plus className="w-4 h-4" /> Add an address
            </button>
          )}
        </>
      )}
    </section>
  );
}
