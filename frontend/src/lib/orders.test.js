/**
 * How an order is described.
 *
 * These are the decisions that reach a customer: the word for each state,
 * whether money is owed, and which stops to draw on the progress trail.
 * Every one of them has been wrong at some point, so each is held here.
 */

import fs from "fs";
import path from "path";
import {
  JOURNEY,
  STATUS_DOT,
  countItems,
  formatDate,
  formatDateTime,
  journeyStops,
  orderedLine,
  paymentName,
  paymentState,
  statusWord,
  whenItReached,
} from "./orders";

/**
 * The states the API can actually store, read from the API.
 *
 * Hard-coding them here would make this file a second copy of the list and
 * defeat the point: the drift it is meant to catch is exactly a status being
 * added in one place and forgotten in the other.
 */
function statusesTheApiCanStore() {
  const models = path.resolve(__dirname, "../../../backend/app/models.py");
  if (!fs.existsSync(models)) {
    throw new Error(
      `Could not find the API's models at ${models}. If the backend has moved, ` +
        "update this path: without it nothing checks that every order state has " +
        "a word to show a customer."
    );
  }
  const source = fs.readFileSync(models, "utf8");
  const block = source.match(/class OrderStatus\(str, Enum\):\n((?:\s+\w+ = "[^"]+"\n)+)/);
  if (!block) {
    throw new Error("Found the API's models but not OrderStatus in them.");
  }
  return [...block[1].matchAll(/"([^"]+)"/g)].map((match) => match[1]);
}

describe("the word for each state", () => {
  const statuses = statusesTheApiCanStore();

  it("covers every state the API can store", () => {
    const missing = statuses.filter((status) => statusWord(status) === status);
    expect(missing).toEqual([]);
  });

  it("gives every state a colour to scan by", () => {
    const missing = statuses.filter((status) => !STATUS_DOT[status]);
    expect(missing).toEqual([]);
  });

  it("says Preparing, not Packed", () => {
    // The shop moves an order here when it has started getting it ready, not
    // when a box is sealed. The stronger word promises what was not done.
    expect(statusWord("processing")).toBe("Preparing");
  });

  it("falls back to the raw value rather than showing nothing", () => {
    expect(statusWord("teleported")).toBe("teleported");
  });
});

describe("whether money is owed", () => {
  it("says so plainly once it is paid", () => {
    expect(paymentState({ payment_status: "paid" })).toEqual({
      text: "Paid",
      settled: true,
    });
  });

  it("asks for nothing on a cancelled order", () => {
    // Telling someone to pay when it arrives, for a parcel that is never
    // coming, is worse than saying nothing at all.
    const cancelled = { status: "cancelled", payment_method: "cod" };
    expect(paymentState(cancelled).text).toBe("Nothing to pay");
    expect(paymentState(cancelled).settled).toBe(true);
  });

  it("treats a delivered cash order as paid", () => {
    const delivered = { status: "delivered", payment_method: "cod" };
    expect(paymentState(delivered)).toEqual({ text: "Paid on delivery", settled: true });
  });

  it("does not make a cash order in transit sound overdue", () => {
    const inTransit = { status: "shipped", payment_method: "cod" };
    expect(paymentState(inTransit)).toEqual({
      text: "Pay when it arrives",
      settled: false,
    });
  });

  it("names the method in words", () => {
    expect(paymentName("cod")).toBe("Cash on Delivery");
    expect(paymentName("upi")).toBe("UPI");
  });
});

describe("when the order reached each state", () => {
  const order = {
    created_at: "2026-10-01T09:00:00Z",
    status: "shipped",
    history: [
      { status: "placed", at: "2026-10-01T09:00:00Z" },
      { status: "processing", at: "2026-10-01T11:30:00Z" },
      { status: "shipped", at: "2026-10-02T08:15:00Z" },
    ],
  };

  it("reads the moment that was recorded", () => {
    expect(whenItReached(order, "shipped")).toBe("2026-10-02T08:15:00Z");
  });

  it("says nothing about a state never reached", () => {
    expect(whenItReached(order, "delivered")).toBeNull();
  });

  it("dates the first stop even with no history at all", () => {
    // Orders from before the shop recorded its own timings still know when
    // they were created, and that one date was there to be used.
    const old = { created_at: "2026-09-20T10:00:00Z", status: "shipped" };
    expect(whenItReached(old, "placed")).toBe("2026-09-20T10:00:00Z");
    expect(whenItReached(old, "shipped")).toBeNull();
  });
});

describe("the stops on the progress trail", () => {
  it("shows the whole route, ticked as far as it has gone", () => {
    const stops = journeyStops({ status: "shipped", history: [] });
    expect(stops.map((stop) => stop.status)).toEqual(JOURNEY);
    expect(stops.map((stop) => stop.done)).toEqual([true, true, true, false]);
  });

  it("ends a cancelled order at the cancellation", () => {
    // Leaving "Delivered" on the route, waiting to be ticked, describes a
    // parcel that is never coming.
    const stops = journeyStops({
      status: "cancelled",
      history: [
        { status: "placed", at: "2026-10-01T09:00:00Z" },
        { status: "processing", at: "2026-10-01T11:00:00Z" },
        { status: "cancelled", at: "2026-10-01T12:00:00Z" },
      ],
    });
    expect(stops.map((stop) => stop.status)).toEqual(["placed", "processing", "cancelled"]);
    expect(stops.every((stop) => stop.done)).toBe(true);
  });

  it("still shows both ends of a cancelled order with no history", () => {
    const stops = journeyStops({ status: "cancelled", created_at: "2026-09-20T10:00:00Z" });
    expect(stops.map((stop) => stop.status)).toEqual(["placed", "cancelled"]);
    expect(stops[0].at).toBe("2026-09-20T10:00:00Z");
  });
});

describe("counting what is in an order", () => {
  it("counts one thing as an item, not items", () => {
    expect(countItems([{ name: "Soap" }])).toBe("1 item");
    expect(countItems([{ name: "Soap" }, { name: "Powder" }])).toBe("2 items");
  });

  it("puts the order date beside the count", () => {
    const line = orderedLine({
      created_at: "2026-10-02T09:00:00Z",
      items: [{ name: "Soap" }],
    });
    expect(line).toContain("2026");
    expect(line).toContain("1 item");
  });
});

describe("showing a date", () => {
  it("says nothing when there is nothing to say", () => {
    expect(formatDate(null)).toBe("");
    expect(formatDate("not a date")).toBe("");
    expect(formatDateTime(null)).toBe("");
  });

  it("carries a time when the steps may share a day", () => {
    // Four identical dates say nothing about the order they happened in.
    expect(formatDateTime("2026-10-02T09:00:00Z")).toMatch(/\d:\d\d/);
    expect(formatDate("2026-10-02T09:00:00Z")).not.toMatch(/\d:\d\d/);
  });
});
