import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../lib/api";

/**
 * The customer's saved addresses.
 *
 * Every change answers with the whole book, so the screen is updated from
 * what the server actually holds rather than from a guess about what the
 * change did.
 */
export default function useAddresses({ enabled = true } = {}) {
  const [addresses, setAddresses] = useState([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState("");
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);

  const load = useCallback(async () => {
    if (!enabled) {
      setAddresses([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.get("/addresses");
      if (alive.current) {
        setAddresses(data.items || []);
        setError("");
      }
    } catch (failure) {
      if (alive.current) setError(errorMessage(failure, "Could not load your addresses."));
    } finally {
      if (alive.current) setLoading(false);
    }
  }, [enabled]);

  useEffect(() => { load(); }, [load]);

  /**
   * Run a change and adopt the book it returns.
   *
   * Refusals are handed back rather than thrown so the caller can show them
   * beside the field they belong to.
   */
  const change = useCallback(async (request, fallback) => {
    try {
      const { data } = await request();
      if (alive.current) setAddresses(data.items || []);
      return { ok: true, items: data.items || [] };
    } catch (failure) {
      return { ok: false, message: errorMessage(failure, fallback), failure };
    }
  }, []);

  const save = useCallback(
    (address) => change(() => api.post("/addresses", address), "Could not save this address."),
    [change]
  );

  const update = useCallback(
    (addressId, address) =>
      change(() => api.put(`/addresses/${addressId}`, address), "Could not save this address."),
    [change]
  );

  const remove = useCallback(
    (addressId) =>
      change(() => api.delete(`/addresses/${addressId}`), "Could not remove this address."),
    [change]
  );

  return { addresses, loading, error, reload: load, save, update, remove };
}
