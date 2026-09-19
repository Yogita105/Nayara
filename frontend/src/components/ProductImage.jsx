import React, { useState } from "react";
import { ImageOff } from "lucide-react";

/**
 * Product image that degrades gracefully.
 *
 * A remote image can disappear or start returning an error page, which the
 * browser renders as a broken icon. Showing a neutral tile instead keeps the
 * layout intact and avoids a page that looks faulty to a customer.
 */
export default function ProductImage({ src, alt = "", className = "", ...props }) {
  // Tracking the failed address, rather than a flag, lets the component
  // recover when it is reused for a different product.
  const [failedSrc, setFailedSrc] = useState(null);
  const unavailable = !src || failedSrc === src;

  if (unavailable) {
    return (
      <div
        className={`flex items-center justify-center bg-[#F1F5F9] text-[#94A3B8] ${className}`}
        role="img"
        aria-label={alt ? `${alt} — image unavailable` : "Image unavailable"}
        data-testid="product-image-fallback"
      >
        <ImageOff className="w-1/3 h-1/3 max-w-10 max-h-10" aria-hidden="true" />
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      loading="lazy"
      onError={() => setFailedSrc(src)}
      {...props}
    />
  );
}
