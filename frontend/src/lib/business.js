/**
 * Who Nayara is and how to reach them.
 *
 * These are the built-in details. The shop's own are set in the admin screen
 * and fetched at startup; these are what shows before that answer arrives,
 * and what stays if it never does. A footer with slightly stale details is
 * better than a footer with none.
 *
 * They mirror DEFAULT_BUSINESS in the API, which serves the same fallback to
 * anyone asking. Two copies, because neither side can reach the other when
 * the request between them is the thing that failed.
 *
 * Prose that happens to mention the town is deliberately not here. "Began in
 * a small workshop in Jaito" is storytelling, and belongs in the sentence it
 * is part of rather than being assembled from parts.
 */

export const DEFAULT_BUSINESS = {
  name: "Nayara Brands",
  founder: "Abhinav Grover",
  founder_title: "Owner",
  address_lines: ["Jaito, District Faridkot", "Punjab 151202, India"],
  phone: "+91 97808 44330",
  hours: "Mon–Sat · 10am–7pm",
  email: "hello@nayara.in",
  wholesale_email: "wholesale@nayara.in",
};

/**
 * The same details, plus the forms a link needs.
 *
 * Derived rather than stored, so what a device dials cannot drift from what
 * a person reads beside it.
 */
export function withContactLinks(settings) {
  const details = { ...DEFAULT_BUSINESS, ...(settings || {}) };
  const lines = details.address_lines?.length
    ? details.address_lines
    : DEFAULT_BUSINESS.address_lines;

  return {
    ...details,
    address_lines: lines,
    addressOneLine: lines.join(", "),
    phoneHref: `tel:${String(details.phone).replace(/[^\d+]/g, "")}`,
    emailHref: `mailto:${details.email}`,
    wholesaleEmailHref: `mailto:${details.wholesale_email}`,
  };
}
