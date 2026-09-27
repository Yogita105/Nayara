import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { DEFAULT_BUSINESS, withContactLinks } from "../lib/business";
import { DEFAULT_SHIPPING } from "../lib/shipping";

/**
 * What the shop says about itself: how to reach it, and what delivery costs.
 *
 * Fetched once for the whole app rather than by each screen that needs it,
 * and it starts from the built-in values rather than from nothing: the
 * footer is on every page, so an empty one would be the first thing a
 * customer sees while the request is in flight. If a request fails the
 * built-in values simply stay, which is a readable footer and a sensible
 * delivery quote rather than blanks.
 */
const BusinessContext = createContext({
  ...withContactLinks(DEFAULT_BUSINESS),
  shipping: DEFAULT_SHIPPING,
  refresh: () => {},
});

export const BusinessProvider = ({ children }) => {
  const [settings, setSettings] = useState(DEFAULT_BUSINESS);
  const [shipping, setShipping] = useState(DEFAULT_SHIPPING);

  const refresh = useCallback(
    () =>
      Promise.all([
        api
          .get("/settings/business")
          .then(({ data }) => setSettings(data))
          .catch(() => {
            // Deliberately silent. A customer cannot act on this, and the
            // details they need are already on the screen.
          }),
        api
          .get("/settings/shipping")
          .then(({ data }) => setShipping(data))
          .catch(() => {}),
      ]),
    []
  );

  useEffect(() => {
    let current = true;
    const keep = (apply) => (response) => {
      if (current) apply(response.data);
    };
    api.get("/settings/business").then(keep(setSettings)).catch(() => {});
    api.get("/settings/shipping").then(keep(setShipping)).catch(() => {});
    return () => {
      current = false;
    };
  }, []);

  // Exposed so the admin screen can say "these changed" after saving.
  // Without it the owner sees their own edit everywhere except the page
  // they are standing on, because nothing remounts on a route change.
  const value = useMemo(
    () => ({ ...withContactLinks(settings), shipping, refresh }),
    [settings, shipping, refresh]
  );
  return <BusinessContext.Provider value={value}>{children}</BusinessContext.Provider>;
};

export const useBusiness = () => useContext(BusinessContext);

/** What delivery costs, as the shop currently charges it. */
export const useShipping = () => useContext(BusinessContext).shipping;
