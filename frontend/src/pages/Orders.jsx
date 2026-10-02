import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Package } from "lucide-react";
import { api, formatINR } from "../lib/api";
import useAsyncData from "../hooks/useAsyncData";
import { EmptyPanel, ErrorPanel, LoadingPanel } from "../components/DataState";
import ProductImage from "../components/ProductImage";
import { lineKey, lineName } from "../lib/variants";
import {
  STATUS_DOT,
  orderedLine,
  paymentName,
  paymentState,
  statusLine,
} from "../lib/orders";

const SHOWN = 3;

function OrderCard({ order }) {
  const payment = paymentState(order);
  const extra = order.items.length - SHOWN;

  return (
    <Link
      to={`/orders/${order.order_id}`}
      className="block rounded-2xl border border-[var(--nayara-border)] bg-white p-6 hover:border-[var(--nayara-primary)] hover:shadow-sm transition"
      data-testid={`order-${order.order_id}`}
    >
      <div className="mb-5">
        <h2
          className="font-heading text-lg font-semibold flex items-center gap-2"
          data-testid="order-status-line"
        >
          <span
            className={`w-2.5 h-2.5 rounded-full shrink-0 ${STATUS_DOT[order.status] || "bg-gray-400"}`}
            aria-hidden="true"
          />
          {statusLine(order)}
        </h2>
        <p className="text-sm text-[#64748B] mt-1">{orderedLine(order)}</p>
      </div>

      <ul className="space-y-3 mb-5">
        {order.items.slice(0, SHOWN).map((item) => (
          <li key={lineKey(item)} className="flex items-center gap-3">
            <ProductImage
              src={item.image}
              alt={lineName(item)}
              width={150}
              className="w-12 h-12 rounded-lg object-cover bg-[#F1F5F9] shrink-0"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{item.name}</p>
              <p className="text-sm text-[#64748B]">
                {item.variant_label ? `${item.variant_label} · ` : ""}
                {item.quantity} × {formatINR(item.price)}
              </p>
            </div>
          </li>
        ))}
        {extra > 0 && (
          <li className="text-sm text-[#64748B]" data-testid="order-more-items">
            and {extra} more {extra === 1 ? "item" : "items"}
          </li>
        )}
      </ul>

      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 pt-4 border-t border-[var(--nayara-border)]">
        <div>
          <p className="text-xs text-[#64748B]">Payment method</p>
          <p className="text-sm font-medium">
            {paymentName(order.payment_method)}
            <span className={`font-normal ${payment.settled ? "text-green-700" : "text-[#64748B]"}`}>
              {" · "}
              {payment.text}
            </span>
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-[#64748B]">Total</p>
          <p className="font-heading text-lg font-semibold">{formatINR(order.total)}</p>
        </div>
        <span
          className="text-sm text-[var(--nayara-primary)] inline-flex items-center gap-1"
          aria-hidden="true"
        >
          View order <ChevronRight className="w-4 h-4" />
        </span>
      </div>
    </Link>
  );
}

export default function Orders() {
  const { data, loading, error, reload } = useAsyncData(
    async () => (await api.get("/orders")).data,
    [],
    "We could not load your orders."
  );
  const orders = data || [];

  return (
    <div className="max-w-3xl mx-auto px-6 py-10" data-testid="orders-page">
      <h1 className="font-heading text-2xl md:text-3xl font-medium tracking-tight mb-8">
        My Orders
      </h1>
      {loading ? (
        <LoadingPanel label="Loading your orders..." />
      ) : error ? (
        <ErrorPanel message={error} onRetry={reload} />
      ) : orders.length === 0 ? (
        <EmptyPanel
          icon={Package}
          message="No orders yet."
          action={<Link to="/shop" className="nayara-btn mt-5">Start Shopping</Link>}
        />
      ) : (
        <div className="space-y-5">
          {orders.map((order) => (
            <OrderCard key={order.order_id} order={order} />
          ))}
        </div>
      )}
    </div>
  );
}
