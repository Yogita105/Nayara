import React from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, MapPin, Package } from "lucide-react";
import { api, formatINR } from "../lib/api";
import useAsyncData from "../hooks/useAsyncData";
import { ErrorPanel, LoadingPanel } from "../components/DataState";
import ProductImage from "../components/ProductImage";
import OrderTotals from "../components/OrderTotals";
import { lineKey, lineName } from "../lib/variants";
import { oneLine } from "../lib/addresses";
import {
  JOURNEY,
  STATUS_DOT,
  formatDate,
  orderedLine,
  statusLine,
  statusWord,
  whenItReached,
} from "../lib/orders";

function Journey({ order }) {
  if (order.status === "cancelled") return null;
  const reached = JOURNEY.indexOf(order.status);

  return (
    <ol className="space-y-4" data-testid="order-journey">
      {JOURNEY.map((step, index) => {
        const done = index <= reached;
        const when = formatDate(whenItReached(order, step));
        return (
          <li key={step} className="flex items-start gap-3">
            <span
              className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                done ? "bg-[var(--nayara-primary)] text-white" : "bg-[#F1F5F9] text-[#94A3B8]"
              }`}
              aria-hidden="true"
            >
              {done ? <Check className="w-3.5 h-3.5" /> : <span className="w-1.5 h-1.5 rounded-full bg-current" />}
            </span>
            <span>
              <span className={`block text-sm ${done ? "font-medium" : "text-[#94A3B8]"}`}>
                {statusWord(step)}
              </span>
              {when && <span className="block text-sm text-[#64748B]">{when}</span>}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export default function OrderDetail() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { data: order, loading, error, reload } = useAsyncData(
    async () => (await api.get(`/orders/${orderId}`)).data,
    [orderId],
    "We could not load this order."
  );

  if (loading) return <LoadingPanel label="Loading your order..." />;
  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-16">
        <ErrorPanel message={error} onRetry={reload} />
        <p className="text-center text-sm text-[#64748B] mt-4">
          <Link to="/orders" className="text-[var(--nayara-primary)] underline">
            Back to your orders
          </Link>
        </p>
      </div>
    );
  }
  if (!order) return null;

  return (
    <div className="max-w-4xl mx-auto px-6 py-10" data-testid="order-detail-page">
      <button
        type="button"
        // History first, so the way back is the way they came. Falling back to
        // the list means a shared or bookmarked link still leads somewhere.
        onClick={() => (window.history.length > 1 ? navigate(-1) : navigate("/orders"))}
        className="inline-flex items-center gap-2 text-sm text-[#64748B] hover:text-[var(--nayara-primary)] mb-6"
        data-testid="order-back"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      <div className="flex flex-col-reverse sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4 mb-2">
        <h1
          className="font-heading text-2xl md:text-3xl font-medium tracking-tight flex items-center gap-3 min-w-0"
          data-testid="order-status-line"
        >
          <span
            className={`w-3 h-3 rounded-full shrink-0 ${STATUS_DOT[order.status] || "bg-gray-400"}`}
            aria-hidden="true"
          />
          {statusWord(order.status)}
        </h1>
        <p className="text-sm text-[#64748B] shrink-0 sm:text-right" data-testid="order-number">
          Order ID - #{order.order_id}
        </p>
      </div>
      <p className="text-[#64748B] mb-8">{orderedLine(order)}</p>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-8">
        <div className="space-y-6">
          <section className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            <h2 className="font-heading font-semibold mb-5 flex items-center gap-2">
              <Package className="w-4 h-4" /> What you ordered
            </h2>
            <ul className="space-y-4" data-testid="order-items">
              {order.items.map((item) => (
                <li key={lineKey(item)} className="flex items-center gap-4">
                  <ProductImage
                    src={item.image}
                    alt={lineName(item)}
                    width={150}
                    className="w-16 h-16 rounded-lg object-cover bg-[#F1F5F9] shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/product/${item.product_id}`}
                      className="font-medium hover:text-[var(--nayara-primary)]"
                    >
                      {item.name}
                    </Link>
                    <p className="text-sm text-[#64748B]">
                      {item.variant_label ? `${item.variant_label} · ` : ""}
                      {item.quantity} × {formatINR(item.price)}
                    </p>
                  </div>
                  <div className="font-semibold shrink-0">
                    {formatINR(item.price * item.quantity)}
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-6 pt-5 border-t border-[var(--nayara-border)]">
              <OrderTotals order={order} testId="order-totals" />
            </div>
          </section>
        </div>

        <aside className="space-y-6">
          <section className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            <h2 className="font-heading font-semibold mb-5">Progress</h2>
            {order.status === "cancelled" ? (
              <p className="text-sm text-[#64748B]" data-testid="order-cancelled">
                {statusLine(order)}
              </p>
            ) : (
              <Journey order={order} />
            )}
          </section>

          <section className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            <h2 className="font-heading font-semibold mb-5 flex items-center gap-2">
              <MapPin className="w-4 h-4" /> Delivery address
            </h2>
            <address className="not-italic text-sm text-[#64748B]" data-testid="order-address">
              <span className="font-medium text-[#0F172A] block">{order.address.full_name}</span>
              <span className="block">{oneLine(order.address)}</span>
              <span className="block">{order.address.phone}</span>
            </address>
          </section>
        </aside>
      </div>
    </div>
  );
}
