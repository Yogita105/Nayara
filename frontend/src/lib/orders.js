/**
 * How an order is described to the person who placed it.
 *
 * The list page and the order page say the same things about an order, so
 * the wording lives here rather than being written twice.
 */

/** "placed" is a database word. This is what a customer is told. */
const STATUS_WORDS = {
  placed: { done: "Ordered", pending: "Ordered" },
  processing: { done: "Packed", pending: "Being packed" },
  shipped: { done: "Dispatched", pending: "On its way" },
  delivered: { done: "Delivered", pending: "Delivered" },
  cancelled: { done: "Cancelled", pending: "Cancelled" },
};

export const STATUS_TONE = {
  placed: "bg-blue-100 text-blue-700",
  processing: "bg-amber-100 text-amber-700",
  shipped: "bg-indigo-100 text-indigo-700",
  delivered: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-700",
};

/** A colour to scan a list by, since the heading already says the word. */
export const STATUS_DOT = {
  placed: "bg-blue-500",
  processing: "bg-amber-500",
  shipped: "bg-indigo-500",
  delivered: "bg-green-600",
  cancelled: "bg-red-500",
};

/** The steps a parcel passes through, in order. Cancelling leaves the path. */
export const JOURNEY = ["placed", "processing", "shipped", "delivered"];

export function statusWord(status) {
  return STATUS_WORDS[status]?.done || status || "Ordered";
}

export function formatDate(value) {
  if (!value) return "";
  const when = new Date(value);
  if (Number.isNaN(when.getTime())) return "";
  return when.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/**
 * A date with the time beside it.
 *
 * A parcel can be ordered, packed, dispatched and delivered inside a day, and
 * four identical dates say nothing about the order they happened in.
 */
export function formatDateTime(value) {
  if (!value) return "";
  const when = new Date(value);
  if (Number.isNaN(when.getTime())) return "";
  return when.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** When the order reached this state, if that was ever recorded. */
export function whenItReached(order, status) {
  const events = order?.history || [];
  const match = [...events].reverse().find((event) => event.status === status);
  return match?.at || null;
}

/**
 * The headline: what happened, and when.
 *
 * Orders placed before the shop recorded its own timings have no date to
 * give, so they say what happened and stop, rather than claiming a date
 * that was never written down.
 */
export function statusLine(order) {
  const word = statusWord(order?.status);
  const when = formatDate(whenItReached(order, order?.status));
  return when ? `${word} on ${when}` : word;
}

const PAYMENT_NAMES = {
  cod: "Cash on Delivery",
  upi: "UPI",
  card: "Card",
};

export function paymentName(method) {
  return PAYMENT_NAMES[method] || (method || "").toUpperCase();
}

/**
 * Whether the money has arrived, said plainly.
 *
 * Cash on Delivery is owed at the door, so an undelivered order is not
 * overdue and must not read as though it were.
 */
export function paymentState(order) {
  if (order?.payment_status === "paid") return { text: "Paid", settled: true };
  if (order?.payment_method === "cod") {
    return order?.status === "delivered"
      ? { text: "Paid on delivery", settled: true }
      : { text: "Pay when it arrives", settled: false };
  }
  if (order?.payment_status === "failed") return { text: "Payment failed", settled: false };
  return { text: "Awaiting payment", settled: false };
}

/** How many lines, so "and 2 more" below it counts the same things. */
export function countItems(items = []) {
  const lines = items.length;
  return `${lines} ${lines === 1 ? "item" : "items"}`;
}

/**
 * The line beneath the heading.
 *
 * The heading names the state the order is in; this says when it was placed
 * and how big it is. When each step happened is on the order's own page.
 */
export function orderedLine(order) {
  const parts = [];
  const when = formatDate(order?.created_at);
  if (when) parts.push(`Ordered on ${when}`);
  parts.push(countItems(order?.items));
  return parts.join(" · ");
}

/** What is in the order, named, for someone deciding whether to open it. */
export function summarise(items = [], upTo = 2) {
  const names = items.map((item) => item.name);
  if (names.length === 0) return "";
  if (names.length <= upTo) return names.join(" and ");
  const extra = names.length - upTo;
  return `${names.slice(0, upTo).join(", ")} and ${extra} more`;
}
