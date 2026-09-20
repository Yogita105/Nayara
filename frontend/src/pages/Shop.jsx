import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ProductCard from "../components/ProductCard";
import Pagination from "../components/Pagination";
import { EmptyPanel, ErrorPanel } from "../components/DataState";
import usePagedData from "../hooks/usePagedData";
import { Search, SlidersHorizontal } from "lucide-react";

const CATEGORIES = [
  { key: "all", label: "All" },
  { key: "laundry", label: "Laundry" },
  { key: "personal-care", label: "Personal Care" },
  { key: "home-care", label: "Home Care" },
];

const SORTS = [
  { key: "popular", label: "Popular" },
  { key: "price_asc", label: "Price: Low to High" },
  { key: "price_desc", label: "Price: High to Low" },
  { key: "rating", label: "Top Rated" },
];

const PAGE_SIZE = 12;
const PRICE_FLOOR = 50;
const PRICE_CEILING = 500;

export default function Shop() {
  const [params, setParams] = useSearchParams();

  const q = params.get("q") || "";
  const category = params.get("category") || "all";
  const sort = SORTS.some((s) => s.key === params.get("sort"))
    ? params.get("sort")
    : "popular";
  const maxPrice = Number(params.get("max_price")) || PRICE_CEILING;

  // Typing and dragging update these at once; the address bar and the request
  // follow when the person pauses, so a search costs one query rather than one
  // per keystroke.
  const [searchText, setSearchText] = useState(q);
  const [priceValue, setPriceValue] = useState(maxPrice);

  useEffect(() => { setSearchText(q); }, [q]);
  useEffect(() => { setPriceValue(maxPrice); }, [maxPrice]);

  const updateParams = useCallback((changes) => {
    setParams((current) => {
      const next = new URLSearchParams(current);
      Object.entries(changes).forEach(([key, value]) => {
        if (value === null || value === "" || value === "all") next.delete(key);
        else next.set(key, value);
      });
      return next;
    });
  }, [setParams]);

  useEffect(() => {
    if (searchText === q) return undefined;
    const timer = setTimeout(() => updateParams({ q: searchText || null }), 300);
    return () => clearTimeout(timer);
  }, [searchText, q, updateParams]);

  useEffect(() => {
    if (priceValue === maxPrice) return undefined;
    const timer = setTimeout(() => {
      updateParams({
        max_price: priceValue >= PRICE_CEILING ? null : String(priceValue),
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [priceValue, maxPrice, updateParams]);

  const query = {
    sort,
    ...(category !== "all" && { category }),
    ...(q && { q }),
    ...(maxPrice < PRICE_CEILING && { max_price: maxPrice }),
  };

  const {
    items: products, total, loading, error, reload,
    page, pageCount, setPage,
  } = usePagedData("/products", {
    pageSize: PAGE_SIZE,
    params: query,
    fallbackMessage: "Products could not be loaded.",
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-10" data-testid="shop-page">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3">Shop</p>
        <h1 className="font-heading text-2xl md:text-3xl font-medium tracking-tighter">All Products</h1>
        <p className="mt-2 text-[#64748B]">Factory-direct cleaning &amp; personal care. Real prices. No middlemen.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-8">
        <aside className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 h-fit" data-testid="shop-filters">
          <div className="flex items-center gap-2 mb-5">
            <SlidersHorizontal className="w-4 h-4" />
            <h3 className="font-heading font-semibold">Filters</h3>
          </div>

          <div className="mb-6">
            <label htmlFor="shop-search" className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-2 block">Search</label>
            <div className="flex items-center bg-[#FFFFFF] rounded-md px-3 h-10">
              <Search className="w-4 h-4 text-[#64748B]" aria-hidden="true" />
              <input
                id="shop-search"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Search products"
                className="bg-transparent outline-none px-2 text-base flex-1"
                data-testid="shop-search-input"
              />
            </div>
          </div>

          <div className="mb-6">
            <span className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3 block">Category</span>
            <div className="flex flex-col gap-2">
              {CATEGORIES.map((c) => (
                <button
                  key={c.key}
                  onClick={() => updateParams({ category: c.key })}
                  className={`text-left px-3 py-2 rounded-md text-sm transition ${category === c.key ? "bg-[var(--nayara-primary)] text-white" : "hover:bg-[#FBEEE4]"}`}
                  data-testid={`filter-category-${c.key}`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mb-6">
            <label htmlFor="shop-price" className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3 block">
              Max Price: ₹{priceValue}
            </label>
            <input
              id="shop-price"
              type="range"
              min={PRICE_FLOOR}
              max={PRICE_CEILING}
              step={10}
              value={priceValue}
              onChange={(e) => setPriceValue(parseInt(e.target.value, 10))}
              className="w-full accent-[var(--nayara-primary)]"
              data-testid="filter-price"
            />
          </div>

          <div>
            <label htmlFor="shop-sort" className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-2 block">Sort</label>
            <select
              id="shop-sort"
              value={sort}
              onChange={(e) => updateParams({ sort: e.target.value })}
              className="w-full border border-[var(--nayara-border)] rounded-md h-10 px-3 text-sm bg-white"
              data-testid="filter-sort"
            >
              {SORTS.map((s) => (
                <option key={s.key} value={s.key}>{s.label}</option>
              ))}
            </select>
          </div>
        </aside>

        <div>
          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="aspect-[3/4] rounded-2xl bg-white animate-pulse" />
              ))}
            </div>
          ) : error ? (
            <ErrorPanel message={error} onRetry={reload} />
          ) : products.length === 0 ? (
            <EmptyPanel
              icon={Search}
              title="No products match your filters"
              message="Try a wider price range or a different category."
            />
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-6" data-testid="shop-grid">
                {products.map((p, i) => <ProductCard key={p.product_id} product={p} index={i} />)}
              </div>
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                pageCount={pageCount}
                total={total}
                onPageChange={setPage}
                noun="products"
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
