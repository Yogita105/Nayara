/**
 * Asking an image host for a size the page will actually use.
 *
 * The home page once pulled 16.9 MB of photographs, its background alone
 * 7.5 MB for a slot no wider than the screen. What is held here is that the
 * request carries a width, and that an address we do not understand is left
 * exactly as it was.
 */

import { IMAGE_WIDTHS, sized, srcSet } from "../../lib/images";

const UNSPLASH = "https://images.unsplash.com/photo-1600857544200-b2f666a9a2ec";

describe("asking for a usable size", () => {
  it("asks for the width the slot needs", () => {
    const asked = new URL(sized(UNSPLASH, 480));
    expect(asked.searchParams.get("w")).toBe("480");
    expect(asked.searchParams.get("q")).toBe("70");
  });

  it("lets the host choose a modern format", () => {
    const asked = new URL(sized(UNSPLASH, 800));
    expect(asked.searchParams.get("auto")).toBe("format");
  });

  it("drops a pinned format that would override that choice", () => {
    const pinned = `${UNSPLASH}?fm=jpg&w=4000`;
    const asked = new URL(sized(pinned, 800));
    expect(asked.searchParams.get("fm")).toBeNull();
    expect(asked.searchParams.get("w")).toBe("800");
  });

  it("keeps the parameters the host already had", () => {
    const withCrop = `${UNSPLASH}?crop=entropy&cs=srgb`;
    const asked = new URL(sized(withCrop, 800));
    expect(asked.searchParams.get("crop")).toBe("entropy");
  });
});

describe("addresses we do not understand", () => {
  it("leaves another host's address exactly as it was", () => {
    // Guessing at another host's parameters breaks the address rather than
    // improving it.
    const elsewhere = "https://cdn.example.com/soap.jpg";
    expect(sized(elsewhere, 800)).toBe(elsewhere);
    expect(srcSet(elsewhere)).toBeUndefined();
  });

  it("copes with nothing at all", () => {
    expect(sized("", 800)).toBe("");
    expect(sized(undefined, 800)).toBeUndefined();
    expect(srcSet(undefined)).toBeUndefined();
  });

  it("returns rubbish unchanged rather than throwing", () => {
    expect(sized("images.unsplash.com not a url", 800)).toBe(
      "images.unsplash.com not a url"
    );
  });
});

describe("offering several widths", () => {
  it("describes each one so the browser can pick", () => {
    const set = srcSet(UNSPLASH);
    IMAGE_WIDTHS.forEach((width) => {
      expect(set).toContain(`${width}w`);
    });
  });
});
