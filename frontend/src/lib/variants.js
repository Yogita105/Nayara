/**
 * Which form of a product the shop is talking about.
 *
 * A product is sold as one or more variants: a weight for powders, a volume
 * for liquids, a colour for soaps. Price, stock and often the photograph
 * belong to the form rather than the product, so almost every screen needs to
 * know which one it is showing.
 */

export function variantsOf(product) {
  return product?.variants || [];
}

export function findVariant(product, variantId) {
  return variantsOf(product).find((variant) => variant.variant_id === variantId) || null;
}

/** Whether the customer has a decision to make. */
export function hasChoice(product) {
  return variantsOf(product).length > 1;
}

/**
 * The form to show before anyone has chosen.
 *
 * The cheapest in stock, because that is the price the grid advertises and
 * landing on a sold-out form asks the customer to fix something they did not
 * do. Everything sold out falls back to the cheapest of those, so the page
 * still has something to show.
 */
export function defaultVariant(product) {
  const byPrice = [...variantsOf(product)].sort((a, b) => (a.price || 0) - (b.price || 0));
  return byPrice.find((variant) => (variant.stock || 0) > 0) || byPrice[0] || null;
}

export function cheapestPrice(product) {
  const prices = variantsOf(product).map((variant) => variant.price);
  return prices.length ? Math.min(...prices) : undefined;
}

/**
 * The form a product is advertised at: the cheapest on offer.
 *
 * The grid shows this one's price and its own MRP. Pairing one form's price
 * with another's MRP would invent a discount neither of them offers.
 */
export function cheapestVariant(product) {
  return variantsOf(product).reduce(
    (best, variant) => (!best || (variant.price || 0) < (best.price || 0) ? variant : best),
    null
  );
}

/** Everything on hand across a product's forms. */
export function totalStock(product) {
  const variants = variantsOf(product);
  if (!variants.length) return undefined;
  return variants.reduce((total, variant) => total + (variant.stock || 0), 0);
}

/**
 * A product as it is actually sold in one form.
 *
 * The price, stock and image of the chosen form stand in for the product's
 * own, under the names every screen already reads, so the pages below do not
 * each have to remember which is which.
 */
export function asSold(product, variant) {
  if (!product || !variant) return product;
  return {
    ...product,
    price: variant.price,
    mrp: variant.mrp ?? variant.price,
    stock: variant.stock ?? 0,
    image: variant.image || product.image,
    variant_id: variant.variant_id,
    variant_label: variant.label,
  };
}

/**
 * What makes a cart line unique.
 *
 * Two forms of one product are two lines, so the identity has to carry both
 * parts. It doubles as a React key and a test handle.
 */
export function lineKey(item) {
  if (!item) return "";
  return item.variant_id ? `${item.product_id}--${item.variant_id}` : item.product_id;
}

/** How a line is named once the product alone is not enough. */
export function lineName(item) {
  return item?.variant_label ? `${item.name} (${item.variant_label})` : item?.name;
}
