import React from "react";
import { formatINR } from "../lib/api";
import { paymentName, paymentState } from "../lib/orders";

/**
 * What an order came to, laid out like the checkout summary the customer
 * already saw.
 *
 * It sits directly under the items because the two are one piece of
 * arithmetic: reading the line prices in one column and hunting for the
 * total in another makes the customer do the adding up.
 */
export default function OrderTotals({ order, testId = "order-totals" }) {
  const payment = paymentState(order);

  return (
    <dl className="text-sm" data-testid={testId}>
      <div className="flex justify-between gap-4 py-1">
        <dt className="text-[#64748B]">Subtotal</dt>
        <dd className="text-right">{formatINR(order.subtotal)}</dd>
      </div>
      <div className="flex justify-between gap-4 py-1">
        <dt className="text-[#64748B]">Delivery</dt>
        <dd className="text-right">
          {order.shipping > 0 ? formatINR(order.shipping) : "Free"}
        </dd>
      </div>
      <div className="flex justify-between gap-4 mt-2 pt-3 border-t border-[var(--nayara-border)] font-heading text-base font-semibold">
        <dt>Total</dt>
        <dd className="text-right" data-testid={`${testId}-total`}>
          {formatINR(order.total)}
        </dd>
      </div>

      <div className="flex justify-between gap-4 py-1 mt-3 pt-3 border-t border-[var(--nayara-border)]">
        <dt className="text-[#64748B]">Payment method</dt>
        <dd className="text-right font-medium">{paymentName(order.payment_method)}</dd>
      </div>
      <div className="flex justify-between gap-4 py-1">
        <dt className="text-[#64748B]">Payment status</dt>
        <dd
          className={`text-right ${payment.settled ? "text-green-700" : ""}`}
          data-testid={`${testId}-payment-state`}
        >
          {payment.text}
        </dd>
      </div>
    </dl>
  );
}
