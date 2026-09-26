/**
 * Who Nayara is and how to reach them.
 *
 * These details were written out in four files, and the phone number in two
 * different shapes: one for a person to read and one for a device to dial.
 * Changing it meant finding every copy, and missing the dialling one would
 * have left a button quietly calling a dead number while the page beside it
 * looked perfectly correct.
 *
 * Prose that happens to mention the town is deliberately not here. "Began in
 * a small workshop in Jaito" is storytelling, and belongs in the sentence it
 * is part of rather than being assembled from parts.
 */

const PHONE = "+91 97808 44330";

export const BUSINESS = {
  name: "Nayara Brands",
  founder: "Abhinav Grover",
  founderTitle: "Owner",

  addressLines: ["Jaito, District Faridkot", "Punjab 151202, India"],

  phone: PHONE,
  // The same number with everything a person reads stripped out, so the link
  // cannot drift from the label beside it.
  phoneHref: `tel:${PHONE.replace(/[^\d+]/g, "")}`,
  hours: "Mon–Sat · 10am–7pm",

  email: "hello@nayara.in",
  wholesaleEmail: "wholesale@nayara.in",
};

/** The address on one line, for places with no room for two. */
export const addressOneLine = BUSINESS.addressLines.join(", ");

export const mailtoHref = (address) => `mailto:${address}`;
