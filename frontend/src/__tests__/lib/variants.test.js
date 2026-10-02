/**
 * Which form of a product the shop is talking about.
 *
 * Price and stock belong to the form, not the product, so choosing the wrong
 * one advertises a price nobody can buy at or lands a customer on something
 * sold out.
 */

import {
  asSold,
  cheapestVariant,
  defaultVariant,
  findVariant,
  hasChoice,
  lineKey,
  lineName,
  totalStock,
  variantsOf,
} from "../../lib/variants";

const powder = {
  product_id: "prod_1",
  name: "Washing Powder",
  image: "product.jpg",
  variants: [
    { variant_id: "v1", label: "1kg", price: 180, mrp: 200, stock: 4 },
    { variant_id: "v2", label: "500g", price: 99, mrp: 120, stock: 0 },
    { variant_id: "v3", label: "2kg", price: 340, stock: 7, image: "big.jpg" },
  ],
};

describe("finding a form", () => {
  it("copes with a product that has none", () => {
    expect(variantsOf(undefined)).toEqual([]);
    expect(findVariant(undefined, "v1")).toBeNull();
    expect(totalStock({})).toBeUndefined();
  });

  it("knows when there is a decision to make", () => {
    expect(hasChoice(powder)).toBe(true);
    expect(hasChoice({ variants: [powder.variants[0]] })).toBe(false);
  });

  it("adds up what is on hand across every form", () => {
    expect(totalStock(powder)).toBe(11);
  });
});

describe("the form to show first", () => {
  it("picks the cheapest that can actually be bought", () => {
    // The cheapest overall is the 500g, but it is sold out: landing there
    // asks the customer to fix something they did not do.
    expect(defaultVariant(powder).variant_id).toBe("v1");
  });

  it("still shows something when every form is sold out", () => {
    const nothingLeft = {
      variants: [
        { variant_id: "a", price: 200, stock: 0 },
        { variant_id: "b", price: 100, stock: 0 },
      ],
    };
    expect(defaultVariant(nothingLeft).variant_id).toBe("b");
  });
});

describe("the price a product is advertised at", () => {
  it("is the cheapest form, in stock or not", () => {
    // The grid advertises a price; whether that form is in stock is a
    // separate question, answered by the sold-out marker.
    expect(cheapestVariant(powder).variant_id).toBe("v2");
  });
});

describe("a product as it is actually sold", () => {
  it("takes price, stock and photograph from the chosen form", () => {
    const sold = asSold(powder, powder.variants[2]);
    expect(sold.price).toBe(340);
    expect(sold.stock).toBe(7);
    expect(sold.image).toBe("big.jpg");
    expect(sold.variant_label).toBe("2kg");
  });

  it("falls back to the product's own photograph", () => {
    expect(asSold(powder, powder.variants[0]).image).toBe("product.jpg");
  });

  it("treats a form with no MRP as not discounted", () => {
    // Pairing a price with a missing MRP once invented a discount.
    const sold = asSold(powder, powder.variants[2]);
    expect(sold.mrp).toBe(sold.price);
  });
});

describe("what makes a cart line unique", () => {
  it("carries both the product and the form", () => {
    // Two forms of one product are two lines, so the identity needs both.
    const oneKg = { product_id: "prod_1", variant_id: "v1" };
    const twoKg = { product_id: "prod_1", variant_id: "v3" };
    expect(lineKey(oneKg)).not.toBe(lineKey(twoKg));
  });

  it("names a line by its form when there is one", () => {
    expect(lineName({ name: "Washing Powder", variant_label: "1kg" })).toBe(
      "Washing Powder (1kg)"
    );
    expect(lineName({ name: "Washing Powder" })).toBe("Washing Powder");
  });
});
