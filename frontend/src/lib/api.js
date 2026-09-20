import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
// In production the API is served from the same origin, so a relative path
// needs no build-time address and keeps cookies first-party.
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

const SAFE_METHODS = ["get", "head", "options"];

let csrfToken = null;

export const setCsrfToken = (token) => {
  csrfToken = token || null;
};

const readCsrfCookie = () => {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
};

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();
  if (!SAFE_METHODS.includes(method)) {
    const token = csrfToken || readCsrfCookie();
    if (token) config.headers["X-CSRF-Token"] = token;
  }
  return config;
});

export const formatINR = (amount) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount || 0);

/**
 * Always produce a string to show the customer.
 *
 * A screen must never be one unexpected response away from a blank page, so
 * anything that is not readable text falls back to a plain sentence.
 */
export const errorMessage = (error, fallback = "Something went wrong. Please try again.") => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;

  const first = error?.response?.data?.errors?.[0]?.message;
  if (typeof first === "string" && first.trim()) return first;

  if (error?.response?.status === 0 || error?.code === "ERR_NETWORK") {
    return "Could not reach the server. Check your connection and try again.";
  }
  return fallback;
};

/**
 * Map the API's per-field errors onto the fields that caused them.
 *
 * Lets a form put each message beside the input it belongs to, rather than
 * showing one sentence and leaving the customer to work out which box is
 * wrong.
 */
export const fieldErrors = (error) => {
  const reported = error?.response?.data?.errors;
  if (!Array.isArray(reported)) return {};

  const byField = {};
  reported.forEach((item) => {
    const field = typeof item?.field === "string" ? item.field : "";
    const message = typeof item?.message === "string" ? item.message : "";
    // Nested paths such as "address.pincode" belong to the last part.
    const name = field.split(".").pop();
    if (name && message && !byField[name]) byField[name] = message;
  });
  return byField;
};
