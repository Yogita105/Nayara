/**
 * Delivery addresses.
 *
 * The same shape is typed at checkout and in the address book, and the
 * server checks it again, so what is held here is that a customer hears
 * about a blank field in words rather than waiting for a round trip.
 */

import {
  EMPTY_ADDRESS,
  deliveryPartOf,
  findProblems,
  oneLine,
  usualAddress,
} from "../../lib/addresses";

const complete = {
  full_name: "Asha Nair",
  phone: "9876500011",
  line1: "12 Mill Road",
  line2: "Near the water tower",
  city: "Pune",
  state: "Maharashtra",
  pincode: "411001",
};

describe("what is missing from an address", () => {
  it("finds nothing wrong with a complete one", () => {
    expect(findProblems(complete)).toEqual({});
  });

  it("asks for each thing a courier needs", () => {
    const problems = findProblems(EMPTY_ADDRESS);
    expect(Object.keys(problems).sort()).toEqual(
      ["city", "full_name", "line1", "phone", "pincode", "state"].sort()
    );
  });

  it("does not count a second address line as missing", () => {
    // Plenty of addresses are one line. Demanding two invents a problem.
    expect(findProblems({ ...complete, line2: "" })).toEqual({});
  });

  it("is not satisfied by blank spaces", () => {
    const problems = findProblems({ ...complete, city: "   " });
    expect(problems.city).toBeTruthy();
  });

  it("complains in sentences, not field names", () => {
    const problems = findProblems(EMPTY_ADDRESS);
    Object.values(problems).forEach((message) => {
      expect(message).toMatch(/^[A-Z].*\.$/);
      // Nobody filling in a delivery address can act on "full_name".
      expect(message).not.toMatch(/full_name|line1|line2|_/);
    });
  });
});

describe("the address on one line", () => {
  it("reads it out the way it would be said", () => {
    expect(oneLine(complete)).toBe(
      "12 Mill Road, Near the water tower, Pune, Maharashtra, 411001"
    );
  });

  it("leaves no gap where a blank line was", () => {
    expect(oneLine({ ...complete, line2: "" })).toBe(
      "12 Mill Road, Pune, Maharashtra, 411001"
    );
  });
});

describe("the address to offer first", () => {
  const home = { address_id: "a1", label: "Home", is_default: false };
  const office = { address_id: "a2", label: "Office", is_default: true };

  it("offers the one the customer chose", () => {
    expect(usualAddress([home, office]).address_id).toBe("a2");
  });

  it("offers the only one there is when none was chosen", () => {
    expect(usualAddress([home]).address_id).toBe("a1");
  });

  it("offers nothing from an empty book", () => {
    expect(usualAddress([])).toBeNull();
    expect(usualAddress(undefined)).toBeNull();
  });
});

describe("the delivery part of a saved address", () => {
  it("drops what belongs to the address book, not the courier", () => {
    const saved = { ...complete, address_id: "a1", label: "Home", is_default: true };
    const forDelivery = deliveryPartOf(saved);
    expect(Object.keys(forDelivery).sort()).toEqual(Object.keys(EMPTY_ADDRESS).sort());
    expect(forDelivery.line1).toBe("12 Mill Road");
  });

  it("fills in blanks rather than leaving fields undefined", () => {
    // An undefined value turns a controlled input into an uncontrolled one,
    // which React complains about and the customer sees as a field that
    // will not type.
    const forDelivery = deliveryPartOf({ full_name: "Asha Nair" });
    Object.values(forDelivery).forEach((value) => expect(typeof value).toBe("string"));
  });
});
