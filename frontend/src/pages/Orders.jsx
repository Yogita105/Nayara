import React, { useEffect, useState } from "react";
import { api, formatINR } from "../lib/api";
import { Link } from "react-router-dom";
import { Package } from "lucide-react";

const STATUS_COLORS = {
  placed: "bg-blue-100 text-blue-700",
  processing: "bg-amber-100 text-amber-700",
  shipped: "bg-indigo-100 text-indigo-700",
  delivered: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-700",
};

export default function Orders() {
  const [orders, setOrders] = useState([]);
  useEffect(() => { api.get("/orders").then(({ data }) => setOrders(data)); }, []);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10" data-testid="orders-page">
      <h1 className="font-heading text-3xl md:text-4xl font-medium tracking-tight mb-8">My Orders</h1>
      {orders.length === 0 ? (
        <div className="text-center py-16 rounded-2xl border border-[var(--nayara-border)] bg-white">
          <Package className="w-14 h-14 mx-auto text-[#64748B] mb-4" />
          <p className="text-[#64748B]">No orders yet.</p>
          <Link to="/shop" className="nayara-btn mt-5">Start Shopping</Link>
        </div>
      ) : (
        <div className="space-y-5">
          {orders.map((o) => (
            <div key={o.order_id} className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6" data-testid={`order-${o.order_id}`}>
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div>
                  <div className="text-xs text-[#64748B]">Order #{o.order_id}</div>
                  <div className="text-xs text-[#64748B]">{new Date(o.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold px-3 py-1 rounded-full ${STATUS_COLORS[o.status] || "bg-gray-100"}`}>{o.status}</span>
                  <span className="text-xs font-semibold px-3 py-1 rounded-full badge-soft">{o.payment_method.toUpperCase()}</span>
                </div>
              </div>
              <div className="flex flex-wrap gap-3 mb-4">
                {o.items.slice(0, 5).map((it) => (
                  <img key={it.product_id} src={it.image} alt="" className="w-14 h-14 rounded-lg object-cover bg-[#F1F5F9]" />
                ))}
                {o.items.length > 5 && <div className="w-14 h-14 rounded-lg bg-[#F1F5F9] flex items-center justify-center text-xs">+{o.items.length - 5}</div>}
              </div>
              <div className="flex justify-between items-center pt-4 border-t border-[var(--nayara-border)]">
                <div className="text-sm text-[#64748B]">{o.items.length} item(s)</div>
                <div className="font-heading text-lg font-semibold">{formatINR(o.total)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
