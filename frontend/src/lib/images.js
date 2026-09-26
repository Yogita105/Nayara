/**
 * Asking an image host for a size the page will actually use.
 *
 * Unsplash serves the full original unless told otherwise. The home page's
 * background was arriving as 7.5 MB for a slot no wider than the screen, and
 * the page as a whole pulled 16.9 MB of photographs. Asking for a width and
 * letting the host choose a modern format takes that background to 233 KB on
 * a desktop and 47 KB on a phone, with nothing visible lost.
 *
 * Addresses from hosts we do not recognise are returned untouched: guessing
 * at another host's parameters would break the address rather than improve
 * it.
 */

const RESIZING_HOSTS = ["images.unsplash.com"];

/** The widths worth offering. Beyond this a phone gains nothing. */
export const IMAGE_WIDTHS = [480, 800, 1280, 1920];

export function sized(url, width) {
  if (!url || !RESIZING_HOSTS.some((host) => url.includes(host))) return url;
  try {
    const address = new URL(url);
    address.searchParams.set("w", String(width));
    address.searchParams.set("q", "70");
    // Let the host answer with avif or webp when the browser says it reads
    // them, and fall back to jpeg when it does not.
    address.searchParams.set("auto", "format");
    // `fm` pins a format and would override that choice.
    address.searchParams.delete("fm");
    return address.toString();
  } catch {
    return url;
  }
}

/**
 * The same picture at several widths, so a phone downloads a phone-sized one.
 *
 * Returns nothing for hosts that cannot resize, which leaves the element with
 * a plain `src` rather than a set of identical addresses.
 */
export function srcSet(url, widths = IMAGE_WIDTHS) {
  if (!url || !RESIZING_HOSTS.some((host) => url.includes(host))) return undefined;
  return widths.map((width) => `${sized(url, width)} ${width}w`).join(", ");
}
