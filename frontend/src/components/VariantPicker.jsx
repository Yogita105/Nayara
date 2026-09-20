import React from "react";
import { formatINR } from "../lib/api";
import { variantsOf } from "../lib/variants";
import ProductImage from "./ProductImage";

/**
 * Choosing which form of a product to buy.
 *
 * Radio buttons rather than styled divs, so the group is announced as a
 * choice and can be worked through with a keyboard. The real inputs are
 * visually hidden and the labels carry the appearance.
 *
 * A sold-out form is shown and can still be selected: seeing that the 1kg is
 * gone while the 500g is not is more use than a button that does nothing.
 */
export default function VariantPicker({ product, value, onChange }) {
  const variants = variantsOf(product);
  if (variants.length <= 1) return null;

  const optionName = product.option_name || "Option";

  return (
    <fieldset className="mt-6" data-testid="variant-picker">
      <legend className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-2">
        {optionName}
      </legend>
      <div className="flex flex-wrap gap-2">
        {variants.map((variant) => {
          const soldOut = (variant.stock || 0) <= 0;
          const inputId = `variant-${variant.variant_id}`;
          return (
            <div key={variant.variant_id}>
              <input
                type="radio"
                id={inputId}
                name="product-variant"
                className="sr-only peer"
                checked={value === variant.variant_id}
                onChange={() => onChange(variant.variant_id)}
              />
              <label
                htmlFor={inputId}
                className="flex items-center gap-2 cursor-pointer rounded-xl border border-[var(--nayara-border)] px-3 py-2 text-sm transition hover:border-[var(--nayara-primary)] peer-checked:border-[var(--nayara-primary)] peer-checked:bg-[#FBEEE4] peer-focus-visible:ring-2 peer-focus-visible:ring-[var(--nayara-primary)] peer-focus-visible:ring-offset-2"
                data-testid={`variant-option-${variant.variant_id}`}
              >
                {variant.image && (
                  <ProductImage
                    src={variant.image}
                    alt=""
                    className="w-8 h-8 rounded-lg object-cover bg-[#F1F5F9]"
                  />
                )}
                <span className="flex flex-col leading-tight">
                  <span className={`font-semibold ${soldOut ? "text-[#94A3B8]" : ""}`}>
                    {variant.label}
                  </span>
                  <span className="text-xs text-[#64748B]">
                    {soldOut ? "Out of stock" : formatINR(variant.price)}
                  </span>
                </span>
              </label>
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}
