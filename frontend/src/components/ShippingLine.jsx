import React from "react";
import { Info } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { formatINR } from "../lib/api";
import { amountToFreeShipping } from "../lib/shipping";

/**
 * The delivery line of an order summary, with the rule behind it.
 *
 * "Shipping ₹49" invites the question "why, and can I avoid it?". The answer
 * was only on the cart page, and only once the basket was already short of
 * the threshold. It is now available wherever the charge appears, on demand
 * rather than as permanent clutter.
 *
 * A popover rather than a tooltip: a tooltip opens on hover, and most of
 * this shop's customers are on a phone, where there is no hover.
 */
export default function ShippingLine({ subtotal, shipping, settings, testId = "summary-shipping" }) {
  const short = amountToFreeShipping(subtotal, settings);
  const free = shipping === 0;

  return (
    <>
      <div className="flex justify-between items-center">
        <span className="text-[#64748B] inline-flex items-center gap-1">
          Shipping
          <Popover>
            <PopoverTrigger asChild>
              <button
                type="button"
                className="text-[#94A3B8] hover:text-[var(--nayara-primary)] rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nayara-primary)]"
                aria-label="Why am I being charged for delivery?"
                data-testid={`${testId}-info`}
              >
                <Info className="w-3.5 h-3.5" aria-hidden="true" />
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-64 text-sm" data-testid={`${testId}-explained`}>
              <p className="font-semibold mb-1">Delivery</p>
              <p className="text-[#64748B] leading-relaxed">
                Orders of {formatINR(settings.free_above)} or more are delivered free.
                Below that, delivery is {formatINR(settings.flat_rate)}.
              </p>
            </PopoverContent>
          </Popover>
        </span>
        <span data-testid={testId}>{free ? "Free" : formatINR(shipping)}</span>
      </div>
      {short > 0 && (
        <div className="text-xs text-[var(--nayara-primary)]" data-testid={`${testId}-nudge`}>
          Add {formatINR(short)} more for free delivery
        </div>
      )}
    </>
  );
}
