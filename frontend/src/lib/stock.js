/**
 * How much stock to admit to, and when.
 *
 * Checkout refuses an order it cannot fill completely, and until now the
 * customer met that refusal only after typing out an address. Saying how many
 * are left while there is still time to change the order turns a failed
 * checkout into a decision made earlier.
 *
 * The exact count is only shown when it is low. A shop that publishes its full
 * inventory on every product tells competitors what it holds, and "47 left"
 * means nothing to a customer buying one.
 */

import { lineName, totalStock } from "./variants";

export const LOW_STOCK_THRESHOLD = 5;

/**
 * Describe a stock level, or return null when there is nothing worth saying.
 */
export function stockNotice(stock) {
  if (typeof stock !== "number") return null;
  if (stock <= 0) {
    return { tone: "out", text: "Out of stock", urgent: true };
  }
  if (stock <= LOW_STOCK_THRESHOLD) {
    return {
      tone: "low",
      text: stock === 1 ? "Only 1 left" : `Only ${stock} left`,
      urgent: true,
    };
  }
  return null;
}

/** Whether this particular form can be ordered. */
export function isOutOfStock(item) {
  return typeof item?.stock === "number" && item.stock <= 0;
}

/**
 * Whether a product has nothing left in any of its forms.
 *
 * A different question from the one above: the grid shows a product before a
 * form has been chosen, so it is only sold out when every form is.
 */
export function isSoldOut(product) {
  const stock = totalStock(product);
  return typeof stock === "number" && stock <= 0;
}

/**
 * The problem with a cart line, if there is one.
 *
 * Wanting more than the shop holds is the case that stops the whole order, so
 * it is named plainly rather than left for checkout to discover.
 */
export function cartLineProblem(item) {
  const stock = item?.stock;
  if (typeof stock !== "number") return null;
  const name = lineName(item);
  if (stock <= 0) {
    return `${name} is out of stock. Remove it to place your order.`;
  }
  if (item.quantity > stock) {
    return `Only ${stock} left of ${name}. Reduce the quantity to place your order.`;
  }
  return null;
}
