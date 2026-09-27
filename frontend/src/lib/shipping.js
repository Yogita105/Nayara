/**
 * What delivery costs.
 *
 * The same figures the API charges with: the cart and the checkout page used
 * to hold their own copies of the threshold, which meant a customer could be
 * quoted one total and billed another the moment the two drifted.
 *
 * The built-in values are the fallback while the answer is in flight, and if
 * it never arrives. They mirror DEFAULT_SHIPPING in the API.
 */

export const DEFAULT_SHIPPING = {
  free_above: 499,
  flat_rate: 49,
};

/** What a basket of this size pays for delivery. */
export function shippingFor(subtotal, settings = DEFAULT_SHIPPING, itemCount = 1) {
  if (!itemCount || subtotal >= settings.free_above) return 0;
  return settings.flat_rate;
}

/** How much more to spend to stop paying for delivery, or nothing to say. */
export function amountToFreeShipping(subtotal, settings = DEFAULT_SHIPPING) {
  const short = settings.free_above - subtotal;
  return short > 0 ? short : 0;
}
