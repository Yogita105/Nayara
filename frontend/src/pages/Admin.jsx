import React, { useEffect, useState } from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import { api, formatINR } from "../lib/api";
import { LayoutDashboard, Package, Users, IndianRupee, ShoppingBag } from "lucide-react";

const navs = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/orders", label: "Orders", icon: ShoppingBag },
  { to: "/admin/products", label: "Products", icon: Package },
  { to: "/admin/users", label: "Users", icon: Users },
];

function Dashboard() {
  const [stats, setStats] = useState(null);
  useEffect(() => { api.get("/admin/stats").then(({ data }) => setStats(data)); }, []);
  if (!stats) return <div>Loading...</div>;
  const cards = [
    { label: "Revenue", value: formatINR(stats.revenue), icon: IndianRupee, color: "var(--nayara-primary)" },
    { label: "Orders", value: stats.total_orders, icon: ShoppingBag, color: "#48CAE4" },
    { label: "Products", value: stats.total_products, icon: Package, color: "#84A98C" },
    { label: "Users", value: stats.total_users, icon: Users, color: "#F59E0B" },
  ];
  return (
    <div data-testid="admin-dashboard">
      <h1 className="font-heading text-3xl font-medium mb-8 tracking-tight">Dashboard</h1>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        {cards.map((c) => (
          <div key={c.label} className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6" data-testid={`stat-${c.label.toLowerCase()}`}>
            <div className="w-10 h-10 rounded-full text-white flex items-center justify-center mb-3" style={{ background: c.color }}>
              <c.icon className="w-5 h-5" />
            </div>
            <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B]">{c.label}</div>
            <div className="font-heading text-2xl font-semibold mt-1">{c.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function OrdersAdmin() {
  const [orders, setOrders] = useState([]);
  const load = () => api.get("/admin/orders").then(({ data }) => setOrders(data));
  useEffect(() => { load(); }, []);
  const update = async (id, status) => {
    await api.put(`/admin/orders/${id}`, { status });
    load();
  };
  return (
    <div data-testid="admin-orders">
      <h1 className="font-heading text-3xl font-medium mb-8 tracking-tight">Orders</h1>
      <div className="rounded-2xl border border-[var(--nayara-border)] bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-[#FFFFFF] text-[#64748B] text-left">
            <tr>
              <th className="px-4 py-3">Order</th><th className="px-4 py-3">Customer</th>
              <th className="px-4 py-3">Total</th><th className="px-4 py-3">Pay</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.order_id} className="border-t border-[var(--nayara-border)]">
                <td className="px-4 py-3 font-mono text-xs">{o.order_id}</td>
                <td className="px-4 py-3">{o.user_email}</td>
                <td className="px-4 py-3">{formatINR(o.total)}</td>
                <td className="px-4 py-3"><span className="badge-soft px-2 py-1 rounded-full text-xs">{o.payment_method}</span></td>
                <td className="px-4 py-3">
                  <select defaultValue={o.status} onChange={(e) => update(o.order_id, e.target.value)} className="border border-[var(--nayara-border)] rounded px-2 py-1 text-xs">
                    {["placed", "processing", "shipped", "delivered", "cancelled"].map((s) => <option key={s}>{s}</option>)}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {orders.length === 0 && <div className="text-center py-8 text-[#64748B]">No orders.</div>}
      </div>
    </div>
  );
}

function ProductsAdmin() {
  const [products, setProducts] = useState([]);
  useEffect(() => { api.get("/products").then(({ data }) => setProducts(data)); }, []);
  return (
    <div data-testid="admin-products">
      <h1 className="font-heading text-3xl font-medium mb-8 tracking-tight">Products</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {products.map((p) => (
          <div key={p.product_id} className="rounded-2xl border border-[var(--nayara-border)] bg-white p-4 flex gap-4">
            <img src={p.image} alt="" className="w-20 h-20 rounded-lg object-cover bg-[#F1F5F9]" />
            <div className="flex-1">
              <h3 className="font-heading font-medium text-sm">{p.name}</h3>
              <div className="text-xs text-[#64748B] mt-1">Stock: {p.stock}</div>
              <div className="font-heading font-semibold mt-2">{formatINR(p.price)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function UsersAdmin() {
  const [users, setUsers] = useState([]);
  useEffect(() => { api.get("/admin/users").then(({ data }) => setUsers(data)); }, []);
  return (
    <div data-testid="admin-users">
      <h1 className="font-heading text-3xl font-medium mb-8 tracking-tight">Users</h1>
      <div className="rounded-2xl border border-[var(--nayara-border)] bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-[#FFFFFF] text-[#64748B] text-left">
            <tr><th className="px-4 py-3">Name</th><th className="px-4 py-3">Email</th><th className="px-4 py-3">Role</th><th className="px-4 py-3">Joined</th></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id} className="border-t border-[var(--nayara-border)]">
                <td className="px-4 py-3">{u.name}</td>
                <td className="px-4 py-3">{u.email}</td>
                <td className="px-4 py-3">{u.is_admin ? <span className="badge-soft px-2 py-1 rounded-full text-xs">Admin</span> : "Customer"}</td>
                <td className="px-4 py-3 text-xs text-[#64748B]">{u.created_at?.slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Admin() {
  const location = useLocation();
  return (
    <div className="max-w-7xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-8" data-testid="admin-page">
      <aside className="rounded-2xl border border-[var(--nayara-border)] bg-white p-3 h-fit">
        {navs.map((n) => {
          const active = n.end ? location.pathname === n.to : location.pathname.startsWith(n.to) && n.to !== "/admin";
          return (
            <Link key={n.to} to={n.to} className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm transition ${active ? "bg-[var(--nayara-primary)] text-white" : "hover:bg-[#FFF4EB]"}`} data-testid={`admin-nav-${n.label.toLowerCase()}`}>
              <n.icon className="w-4 h-4" /> {n.label}
            </Link>
          );
        })}
      </aside>
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="orders" element={<OrdersAdmin />} />
        <Route path="products" element={<ProductsAdmin />} />
        <Route path="users" element={<UsersAdmin />} />
      </Routes>
    </div>
  );
}
