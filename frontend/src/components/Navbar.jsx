import React, { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { ShoppingCart, Heart, Search, User, LogOut, Menu, X, Package, LayoutDashboard } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Button } from "./ui/button";

const navLinks = [
  { to: "/", label: "Home" },
  { to: "/shop", label: "Shop" },
  { to: "/bulk", label: "Bulk Orders" },
  { to: "/about", label: "About" },
  { to: "/contact", label: "Contact" },
];

export default function Navbar() {
  const { user, loading, logout } = useAuth();
  const { cartCount } = useCart();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  const onSearch = (e) => {
    e.preventDefault();
    if (q.trim()) navigate(`/shop?q=${encodeURIComponent(q.trim())}`);
  };

  const onLogout = async () => {
    try {
      await logout();
      navigate("/");
    } catch {
      toast.error("Could not log out. Please try again.");
    }
  };

  return (
    <header className="glass-nav fixed top-0 inset-x-0 z-50" data-testid="site-navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2" data-testid="nav-logo-link">
          <div className="w-9 h-9 rounded-full flex items-center justify-center text-white font-bold" style={{ background: "var(--nayara-primary)" }}>N</div>
          <span className="font-heading text-2xl font-semibold tracking-tight text-white">Nayara</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) =>
                `text-base font-medium transition-colors ${isActive ? "text-white font-bold" : "text-white/80 hover:text-white"}`
              }
              data-testid={`nav-link-${l.label.toLowerCase()}`}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>

        <form onSubmit={onSearch} className="hidden lg:flex items-center bg-white border border-[var(--nayara-border)] rounded-full px-3 h-10 w-64" data-testid="nav-search-form">
          <Search className="w-5 h-5 text-[#64748B]" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search products..."
            className="bg-transparent outline-none px-2 text-base flex-1"
            data-testid="nav-search-input"
          />
        </form>

        <div className="flex items-center gap-1">
          <Link to="/wishlist" className="p-2 rounded-full hover:bg-white/20 transition-colors text-white" data-testid="nav-wishlist-link" aria-label="Wishlist">
            <Heart className="w-6 h-6" />
          </Link>
          <Link to="/cart" className="relative p-2 rounded-full hover:bg-white/20 transition-colors text-white" data-testid="nav-cart-link" aria-label="Cart">
            <ShoppingCart className="w-6 h-6" />
            {cartCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-5 h-5 px-1 rounded-full bg-[var(--nayara-secondary)] text-white text-[11px] font-semibold flex items-center justify-center" data-testid="nav-cart-count">
                {cartCount}
              </span>
            )}
          </Link>

          {loading ? (
            <div
              className="flex items-center gap-2 p-1 pr-3"
              aria-label="Loading account"
              data-testid="nav-auth-loading"
            >
              <div className="w-8 h-8 rounded-full bg-white/25 animate-pulse" />
              <div className="hidden sm:block w-12 h-4 rounded bg-white/25 animate-pulse" />
            </div>
          ) : user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 p-1 pr-3 rounded-full hover:bg-white/20 transition-colors text-white" data-testid="nav-user-menu">
                  {user.picture ? (
                    <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full object-cover" />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-[var(--nayara-secondary)] text-white flex items-center justify-center text-base font-semibold">{user.name?.[0]?.toUpperCase()}</div>
                  )}
                  <span className="hidden sm:inline text-base font-medium text-white">{user.name?.split(" ")[0]}</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" data-testid="nav-user-dropdown">
                <DropdownMenuItem onClick={() => navigate("/orders")} data-testid="nav-orders-item">
                  <Package className="w-4 h-4 mr-2" /> My Orders
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate("/wishlist")}>
                  <Heart className="w-4 h-4 mr-2" /> Wishlist
                </DropdownMenuItem>
                {user.is_admin && (
                  <DropdownMenuItem onClick={() => navigate("/admin")} data-testid="nav-admin-item">
                    <LayoutDashboard className="w-4 h-4 mr-2" /> Admin
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={onLogout} data-testid="nav-logout-item">
                  <LogOut className="w-4 h-4 mr-2" /> Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Link to="/login" data-testid="nav-login-link">
              <Button className="rounded-full bg-white text-[var(--nayara-primary)] hover:bg-white/90">
                <User className="w-5 h-5 mr-1" /> Login
              </Button>
            </Link>
          )}

          <button className="md:hidden p-2 text-white" onClick={() => setOpen((o) => !o)} data-testid="nav-mobile-toggle" aria-label="Menu">
            {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="md:hidden border-t border-[var(--nayara-border)] bg-white" data-testid="nav-mobile-menu">
          <div className="px-4 py-3 flex flex-col gap-2">
            {navLinks.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                onClick={() => setOpen(false)}
                className="py-2 text-base font-medium"
                data-testid={`mobile-nav-${l.label.toLowerCase()}`}
              >
                {l.label}
              </Link>
            ))}
            <form onSubmit={onSearch} className="flex items-center bg-[#FFFFFF] rounded-full px-3 h-10 mt-2">
              <Search className="w-5 h-5 text-[#64748B]" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search" className="bg-transparent outline-none px-2 text-base flex-1" />
            </form>
          </div>
        </div>
      )}
    </header>
  );
}
