import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../lib/api";

/**
 * Load data for a screen, tracking whether it is still arriving or failed.
 *
 * Screens previously set only the data, so a failed request left the loading
 * message on screen permanently with no way to retry.
 */
export default function useAsyncData(fetcher, deps = [], fallbackMessage) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const alive = useRef(true);

  // Reset on every mount: React's development double-mount would otherwise
  // leave this false forever and the screen would never leave "Loading".
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);

  const run = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const data = await fetcher();
      if (alive.current) setState({ data, loading: false, error: null });
    } catch (failure) {
      if (alive.current) {
        setState({
          data: null,
          loading: false,
          error: errorMessage(failure, fallbackMessage),
        });
      }
    }
    // The caller passes the values the fetcher actually depends on; the
    // fetcher itself is redefined on every render and cannot be listed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { run(); }, [run]);

  return { ...state, reload: run };
}
