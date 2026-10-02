/**
 * How an order is described, on every screen that describes one.
 *
 * The orders list, the order page and the admin table all say the same
 * things about an order, so the wording lives here rather than being written
 * out separately in each and drifting apart.
 */

/**
 * The word for each state.
 *
 * "processing" is a database word. It is stored, never shown: the shop and
 * the customer both read the labels below, so there is nowhere for a second
 * vocabulary to grow. A customer quoting "Preparing" is quoting what the
 * owner sees too.
 *
 * "Preparing" rather than "Packed" deliberately. The shop moves an order here
 * when it has accepted it and started getting it ready, which is not the same
 * as a box being sealed. Claiming the stronger of the two would have the shop
 * promising something it had not done.
 */
const STATUS_WORDS = {
  placed: "Ordered",
  processing: "Preparing",
  shipped: "Dispatched",
  delivered: "Delivered",
  cancelled: "Cancelled",
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

/**
 * The stops to draw for this order.
 *
 * A cancelled order shows only where it actually got to, ending at the
 * cancellation: a delivery that will never happen is not something to leave
 * on the route waiting to be ticked. Every other order shows the full path,
 * so what is still to come is visible.
 */
export function journeyStops(order) {
  if (order?.status === "cancelled") {
    const reached = [];
    for (const event of order.history || []) {
      if (!reached.includes(event.status)) reached.push(event.status);
    }
    if (!reached.includes("placed")) reached.unshift("placed");
    if (!reached.includes("cancelled")) reached.push("cancelled");
    return reached.map((status) => ({
      status,
      at: whenItReached(order, status),
      done: true,
    }));
  }

  const furthest = JOURNEY.indexOf(order?.status);
  return JOURNEY.map((status, index) => ({
    status,
    at: whenItReached(order, status),
    done: index <= furthest,
  }));
}

export function statusWord(status) {
  return STATUS_WORDS[status] || status || "Ordered";
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

/**
 * When the order reached this state, if that was ever recorded.
 *
 * Being placed is the exception: every order carries the moment it was
 * created, so that stop can always be dated even for orders from before the
 * shop recorded its own timings. The later stops on those orders genuinely
 * have no answer, and say nothing rather than guessing.
 */
export function whenItReached(order, status) {
  const events = order?.history || [];
  const match = [...events].reverse().find((event) => event.status === status);
  if (match?.at) return match.at;
  return status === "placed" ? order?.created_at || null : null;
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
 * overdue and must not read as though it were. A cancelled order owes
 * nothing at all: telling someone to pay when it arrives, for a parcel that
 * is never coming, is worse than saying nothing.
 */
export function paymentState(order) {
  if (order?.payment_status === "paid") return { text: "Paid", settled: true };
  if (order?.status === "cancelled") return { text: "Nothing to pay", settled: true };
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
