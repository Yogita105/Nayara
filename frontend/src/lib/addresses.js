/**
 * Delivery addresses, shared by checkout and the address book.
 *
 * The same shape is typed in both places, so the blank form and the checks
 * live here rather than being written twice and drifting apart.
 */

export const EMPTY_ADDRESS = {
  full_name: "",
  phone: "",
  line1: "",
  line2: "",
  city: "",
  state: "",
  pincode: "",
};

/** Keep only the delivery fields, dropping anything the book adds. */
export function deliveryPartOf(address) {
  return Object.keys(EMPTY_ADDRESS).reduce(
    (kept, field) => ({ ...kept, [field]: address?.[field] ?? "" }),
    {}
  );
}

/**
 * What is missing before this address could be delivered to.
 *
 * The server checks the same things and is the authority; this exists so a
 * customer hears about a blank field without waiting for a round trip.
 */
export function findProblems(address) {
  const problems = {};
  if ((address.full_name || "").trim().length < 2) {
    problems.full_name = "Enter the name for this delivery.";
  }
  if (!(address.phone || "").trim()) problems.phone = "Enter a phone number for the courier.";
  if (!(address.line1 || "").trim()) problems.line1 = "Enter the street address.";
  if (!(address.city || "").trim()) problems.city = "Enter the city.";
  if (!(address.state || "").trim()) problems.state = "Enter the state.";
  if (!(address.pincode || "").trim()) problems.pincode = "Enter the PIN code.";
  return problems;
}

/** The address on one line, the way it would be read out. */
export function oneLine(address) {
  return [address.line1, address.line2, address.city, address.state, address.pincode]
    .map((part) => (part || "").trim())
    .filter(Boolean)
    .join(", ");
}

/** The saved address to offer first: the chosen one, else the only one. */
export function usualAddress(saved) {
  if (!saved?.length) return null;
  return saved.find((address) => address.is_default) || saved[0];
}
