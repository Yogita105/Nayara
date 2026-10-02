/**
 * What delivery costs.
 *
 * These figures are a copy of the API's, kept so the cart can quote a total
 * before the real settings arrive. A copy that drifts quotes a customer one
 * price and charges another, so the copy itself is checked against the
 * original here.
 */

import fs from "fs";
import path from "path";
import { DEFAULT_SHIPPING, amountToFreeShipping, shippingFor } from "./shipping";

/** The API's own fallback, read from the API rather than written out again. */
function apiDefaults() {
  const models = path.resolve(__dirname, "../../../backend/app/models.py");
  if (!fs.existsSync(models)) {
    throw new Error(
      `Could not find the API's models at ${models}. If the backend has moved, ` +
        "update this path: without it nothing checks that the delivery charge " +
        "shown matches the one the shop bills."
    );
  }
  const source = fs.readFileSync(models, "utf8");
  const block = source.match(/DEFAULT_SHIPPING = ShippingSettings\(([^)]*)\)/s);
  if (!block) {
    throw new Error("Found the API's models but not DEFAULT_SHIPPING in them.");
  }
  const read = (field) => {
    const found = block[1].match(new RegExp(`${field}\\s*=\\s*([\\d.]+)`));
    return found ? Number(found[1]) : undefined;
  };
  return { free_above: read("free_above"), flat_rate: read("flat_rate") };
}

describe("the copy of the delivery charge", () => {
  it("matches the one the API bills with", () => {
    // A customer quoted one total and billed another would be our fault, and
    // the two numbers live in different languages with nothing between them.
    expect(DEFAULT_SHIPPING).toEqual(apiDefaults());
  });
});

describe("what a basket pays for delivery", () => {
  const settings = { free_above: 499, flat_rate: 49 };

  it("charges nothing once the basket is big enough", () => {
    expect(shippingFor(499, settings, 1)).toBe(0);
    expect(shippingFor(1000, settings, 3)).toBe(0);
  });

  it("charges the flat rate below that", () => {
    expect(shippingFor(498, settings, 1)).toBe(49);
  });

  it("charges nothing for an empty basket", () => {
    // An empty basket is not a delivery, so it is not billed for one.
    expect(shippingFor(0, settings, 0)).toBe(0);
  });
});

describe("how much more to spend for free delivery", () => {
  const settings = { free_above: 499, flat_rate: 49 };

  it("counts the shortfall", () => {
    expect(amountToFreeShipping(400, settings)).toBe(99);
  });

  it("asks for nothing once the basket is there", () => {
    expect(amountToFreeShipping(499, settings)).toBe(0);
    expect(amountToFreeShipping(600, settings)).toBe(0);
  });
});
