import React from "react";

/**
 * Marks a field the customer must fill in.
 *
 * Hidden from assistive technology because the input itself carries the
 * `required` attribute, which screen readers already announce. Showing it
 * twice would read as "star, required".
 */
export default function RequiredMark() {
  return (
    <span className="text-red-500 ml-0.5" aria-hidden="true">
      *
    </span>
  );
}
