import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { DEFAULT_BUSINESS, withContactLinks } from "../lib/business";

/**
 * How to reach the shop, as the shop currently says it.
 *
 * Fetched once for the whole app rather than by each screen that needs it,
 * and it starts from the built-in details rather than from nothing: the
 * footer is on every page, so an empty one would be the first thing a
 * customer sees while the request is in flight. If the request fails the
 * built-in details simply stay, which is a readable footer rather than a
 * blank space where a phone number should be.
 */
const BusinessContext = createContext({
  ...withContactLinks(DEFAULT_BUSINESS),
  refresh: () => {},
});

export const BusinessProvider = ({ children }) => {
  const [settings, setSettings] = useState(DEFAULT_BUSINESS);

  const refresh = useCallback(
    () =>
      api
        .get("/settings/business")
        .then(({ data }) => setSettings(data))
        .catch(() => {
          // Deliberately silent. A customer cannot act on this, and the
          // details they need are already on the screen.
        }),
    []
  );

  useEffect(() => {
    let current = true;
    api
      .get("/settings/business")
      .then(({ data }) => {
        if (current) setSettings(data);
      })
      .catch(() => {});
    return () => {
      current = false;
    };
  }, []);

  // Exposed so the admin screen can say "these changed" after saving.
  // Without it the owner sees their own edit everywhere except the page
  // they are standing on, because nothing remounts on a route change.
  const value = useMemo(() => ({ ...withContactLinks(settings), refresh }), [settings, refresh]);
  return <BusinessContext.Provider value={value}>{children}</BusinessContext.Provider>;
};

export const useBusiness = () => useContext(BusinessContext);
