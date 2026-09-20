import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../lib/api";

const TOTAL_HEADER = "x-total-count";

/**
 * Load one page of a list endpoint and report how many records exist.
 *
 * Without paging these screens asked for a fixed cap and displayed whatever
 * came back, so once a shop passed that many orders the oldest simply stopped
 * appearing and nothing said so.
 */
export default function usePagedData(
  path,
  { pageSize = 25, params, fallbackMessage } = {}
) {
  const [page, setPage] = useState(0);
  const [state, setState] = useState({
    items: [],
    total: 0,
    loading: true,
    error: null,
  });
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);

  // Comparing the serialised form keeps a caller's inline object from
  // looking like a new value on every render.
  const paramKey = JSON.stringify(params || {});

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const response = await api.get(path, {
        params: { ...JSON.parse(paramKey), limit: pageSize, offset: page * pageSize },
      });
      const items = response.data || [];
      const reported = Number(response.headers?.[TOTAL_HEADER]);
      if (alive.current) {
        setState({
          items,
          // Without the header, assume there is another page whenever this
          // one came back full.
          total: Number.isFinite(reported) && reported >= 0
            ? reported
            : page * pageSize + items.length + (items.length === pageSize ? 1 : 0),
          loading: false,
          error: null,
        });
      }
    } catch (failure) {
      if (alive.current) {
        setState({
          items: [],
          total: 0,
          loading: false,
          error: errorMessage(failure, fallbackMessage),
        });
      }
    }
  }, [path, paramKey, pageSize, page, fallbackMessage]);

  useEffect(() => { load(); }, [load]);

  // A filter change can leave someone stranded past the end of a shorter list.
  useEffect(() => { setPage(0); }, [paramKey, pageSize]);

  const pageCount = Math.max(1, Math.ceil(state.total / pageSize));

  return {
    ...state,
    page,
    pageSize,
    pageCount,
    setPage,
    reload: load,
    isFirstPage: page === 0,
    isLastPage: page >= pageCount - 1,
  };
}
