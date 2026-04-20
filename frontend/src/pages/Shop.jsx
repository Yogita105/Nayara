import React, { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import ProductCard from "../components/ProductCard";
import { api } from "../lib/api";
import { Search, SlidersHorizontal } from "lucide-react";

const CATEGORIES = [
  { key: "all", label: "All" },
  { key: "laundry", label: "Laundry" },
  { key: "personal-care", label: "Personal Care" },
  { key: "home-care", label: "Home Care" },
];

export default function Shop() {
  const [params, setParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState("popular");
  const [priceRange, setPriceRange] = useState([0, 500]);

  const q = params.get("q") || "";
  const category = params.get("category") || "all";

  useEffect(() => {
    setLoading(true);
    const p = {};
    if (category && category !== "all") p.category = category;
    if (q) p.q = q;
    api.get("/products", { params: p }).then(({ data }) => {
      setProducts(data);
      setLoading(false);
    });
  }, [q, category]);

  const setCategory = (cat) => {
    const np = new URLSearchParams(params);
    if (cat === "all") np.delete("category"); else np.set("category", cat);
    setParams(np);
  };
  const setQuery = (val) => {
    const np = new URLSearchParams(params);
    if (val) np.set("q", val); else np.delete("q");
    setParams(np);
  };

  const filtered = useMemo(() => {
    let arr = products.filter((p) => p.price >= priceRange[0] && p.price <= priceRange[1]);
    if (sort === "price_asc") arr = [...arr].sort((a, b) => a.price - b.price);
    else if (sort === "price_desc") arr = [...arr].sort((a, b) => b.price - a.price);
    else if (sort === "rating") arr = [...arr].sort((a, b) => b.rating - a.rating);
    return arr;
  }, [products, priceRange, sort]);

  return (
    <div className="max-w-7xl mx-auto px-6 py-10" data-testid="shop-page">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#5C7671] mb-3">Shop</p>
        <h1 className="font-heading text-4xl md:text-5xl font-medium tracking-tighter">All Products</h1>
        <p className="mt-2 text-[#5C7671]">Factory-direct cleaning & personal care. Real prices. No middlemen.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-8">
        {/* Filters */}
        <aside className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 h-fit" data-testid="shop-filters">
          <div className="flex items-center gap-2 mb-5">
            <SlidersHorizontal className="w-4 h-4" />
            <h3 className="font-heading font-semibold">Filters</h3>
          </div>

          <div className="mb-6">
            <label className="text-xs uppercase tracking-[0.2em] font-bold text-[#5C7671] mb-2 block">Search</label>
            <div className="flex items-center bg-[#F8F9FA] rounded-md px-3 h-10">
              <Search className="w-4 h-4 text-[#5C7671]" />
              <input
                value={q}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search products"
                className="bg-transparent outline-none px-2 text-sm flex-1"
                data-testid="shop-search-input"
              />
            </div>
          </div>

          <div className="mb-6">
            <label className="text-xs uppercase tracking-[0.2em] font-bold text-[#5C7671] mb-3 block">Category</label>
            <div className="flex flex-col gap-2">
              {CATEGORIES.map((c) => (
                <button
                  key={c.key}
                  onClick={() => setCategory(c.key)}
                  className={`text-left px-3 py-2 rounded-md text-sm transition ${category === c.key ? "bg-[var(--nayara-primary)] text-white" : "hover:bg-[#E8F1F2]"}`}
                  data-testid={`filter-category-${c.key}`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mb-6">
            <label className="text-xs uppercase tracking-[0.2em] font-bold text-[#5C7671] mb-3 block">Max Price: ₹{priceRange[1]}</label>
            <input
              type="range"
              min={50}
              max={500}
              step={10}
              value={priceRange[1]}
              onChange={(e) => setPriceRange([0, parseInt(e.target.value)])}
              className="w-full accent-[var(--nayara-primary)]"
              data-testid="filter-price"
            />
          </div>

          <div>
            <label className="text-xs uppercase tracking-[0.2em] font-bold text-[#5C7671] mb-2 block">Sort</label>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="w-full border border-[var(--nayara-border)] rounded-md h-10 px-3 text-sm bg-white"
              data-testid="filter-sort"
            >
              <option value="popular">Popular</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="rating">Top Rated</option>
            </select>
          </div>
        </aside>

        <div>
          <div className="mb-5 text-sm text-[#5C7671]">
            Showing <span className="font-semibold text-[#1A2E2A]">{filtered.length}</span> products
          </div>
          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="aspect-[3/4] rounded-2xl bg-white animate-pulse" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-20 text-[#5C7671]">No products match your filters.</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6" data-testid="shop-grid">
              {filtered.map((p, i) => <ProductCard key={p.product_id} product={p} index={i} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
