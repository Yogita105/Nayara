/**
 * How much stock to admit to, and when.
 *
 * "Out of stock" is two questions wearing one name: the grid asks whether a
 * product has anything left in any form, the product page asks about the one
 * form chosen. Answering the wrong one hides things that are on sale.
 */

import { cartLineProblem, isOutOfStock, isSoldOut, stockNotice } from "./stock";

describe("what to say about a stock level", () => {
  it("says nothing when there is plenty", () => {
    // Publishing the full count tells competitors what the shop holds, and
    // "47 left" means nothing to someone buying one.
    expect(stockNotice(47)).toBeNull();
  });

  it("counts down out loud when it is nearly gone", () => {
    expect(stockNotice(3).text).toBe("Only 3 left");
    expect(stockNotice(1).text).toBe("Only 1 left");
  });

  it("says so plainly when there is none", () => {
    expect(stockNotice(0).text).toBe("Out of stock");
  });

  it("says nothing at all when the count is unknown", () => {
    expect(stockNotice(undefined)).toBeNull();
    expect(stockNotice(null)).toBeNull();
  });
});

describe("the two senses of sold out", () => {
  const partlyAvailable = {
    variants: [
      { variant_id: "v1", stock: 0 },
      { variant_id: "v2", stock: 6 },
    ],
  };

  it("does not call a product sold out while one form remains", () => {
    expect(isSoldOut(partlyAvailable)).toBe(false);
  });

  it("calls the empty form out of stock even so", () => {
    expect(isOutOfStock(partlyAvailable.variants[0])).toBe(true);
    expect(isOutOfStock(partlyAvailable.variants[1])).toBe(false);
  });

  it("calls a product sold out only when every form is", () => {
    expect(isSoldOut({ variants: [{ stock: 0 }, { stock: 0 }] })).toBe(true);
  });

  it("makes no claim about a product whose stock is unknown", () => {
    expect(isSoldOut({})).toBe(false);
    expect(isOutOfStock({})).toBe(false);
  });
});

describe("the problem with a cart line", () => {
  it("names a line that cannot be ordered at all", () => {
    const problem = cartLineProblem({
      name: "Washing Powder",
      variant_label: "1kg",
      stock: 0,
      quantity: 1,
    });
    expect(problem).toContain("Washing Powder (1kg)");
    expect(problem).toContain("Remove it");
  });

  it("says how many are left when the basket asks for too many", () => {
    // An order is all or nothing, so this is what would stop the whole
    // checkout. Saying it in the cart is saying it while it can be acted on.
    const problem = cartLineProblem({ name: "Soap", stock: 2, quantity: 5 });
    expect(problem).toContain("Only 2 left");
  });

  it("finds no problem with a line the shop can fill", () => {
    expect(cartLineProblem({ name: "Soap", stock: 9, quantity: 2 })).toBeNull();
  });
});
