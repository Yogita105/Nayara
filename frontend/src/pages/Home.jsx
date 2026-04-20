import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Leaf, ShieldCheck, Factory, Sparkles, Truck, Home as HomeIcon, X, IndianRupee, Package, BadgeCheck, Award } from "lucide-react";
import ProductCard from "../components/ProductCard";
import { api } from "../lib/api";

export default function Home() {
  const [featured, setFeatured] = useState([]);

  useEffect(() => {
    api.get("/products?featured=true").then(({ data }) => setFeatured(data.slice(0, 4)));
  }, []);

  return (
    <div data-testid="home-page">
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: "url('https://images.unsplash.com/photo-1632834702267-8da808897480?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzOTB8MHwxfHNlYXJjaHwxfHxjbGVhbiUyMHdhdGVyJTIwc3BsYXNoJTIwYmFja2dyb3VuZHxlbnwwfHx8fDE3NzY2ODM4Nzh8MA&ixlib=rb-4.1.0&q=85')" }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-white/80 via-white/70 to-[#FFFFFF]" />
        <div className="relative max-w-7xl mx-auto px-6 pt-16 pb-28 lg:pt-24 lg:pb-40">
          <span className="badge-soft px-4 py-1.5 rounded-full text-xs font-semibold inline-flex items-center gap-1.5" data-testid="hero-badge">
            <Leaf className="w-3.5 h-3.5" /> Made in India · Factory Direct
          </span>
          <h1 className="mt-6 font-heading text-4xl sm:text-5xl lg:text-6xl font-medium max-w-3xl tracking-tighter leading-[1.05]">
            Thoughtful cleaning.<br />
            <span className="text-[var(--nayara-primary)]">Everyday freshness.</span>
          </h1>
          <p className="mt-6 max-w-xl text-[#64748B] text-base md:text-lg leading-relaxed">
            Premium laundry, personal and home care crafted in small batches for Indian homes. Real ingredients. Real value. Delivered straight from our factory floor.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/shop" className="nayara-btn" data-testid="hero-shop-btn">
              Shop Collection <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
            <Link to="/about" className="nayara-btn-outline" data-testid="hero-story-btn">Our Story</Link>
          </div>
          <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
            {[
              { icon: Factory, label: "Factory Direct" },
              { icon: ShieldCheck, label: "Skin-safe formulas" },
              { icon: Truck, label: "Free shipping ₹499+" },
              { icon: Sparkles, label: "Small-batch made" },
            ].map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-[#0F172A]">
                <f.icon className="w-5 h-5 text-[var(--nayara-primary)]" />
                <span className="font-medium">{f.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FACTORY-DIRECT BANNER */}
      <section className="relative overflow-hidden" data-testid="factory-direct-banner">
        <div className="absolute inset-0" style={{ background: "linear-gradient(135deg, var(--nayara-primary) 0%, var(--nayara-primary-hover) 100%)" }} />
        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: "radial-gradient(circle at 20% 20%, rgba(255,255,255,.25) 0, transparent 40%), radial-gradient(circle at 80% 80%, rgba(255,255,255,.2) 0, transparent 40%)" }} />
        <div className="relative max-w-7xl mx-auto px-6 py-20 lg:py-24 text-white">
          <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-12 items-center">
            {/* Left — headline */}
            <div>
              <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold bg-white/15 backdrop-blur-sm border border-white/20">
                <BadgeCheck className="w-3.5 h-3.5" /> Save up to 30%
              </span>
              <h2 className="mt-5 font-heading text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tighter leading-[1.03]" data-testid="factory-direct-headline">
                Factory Direct.<br />
                <span className="italic text-white/90">No Middlemen.</span>
              </h2>
              <p className="mt-6 text-base md:text-lg text-white/90 max-w-xl leading-relaxed">
                Every bottle, bar and pack ships straight from our Punjab factory to your doorstep. Skip the 4 layers of distributors, wholesalers and retailers — and keep their margins in your wallet.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/shop" className="inline-flex items-center justify-center rounded-md px-6 py-3 font-medium bg-white text-[var(--nayara-primary-hover)] hover:bg-white/90 transition-all duration-300 hover:-translate-y-0.5" data-testid="banner-shop-btn">
                  Shop Factory-Direct <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
                <Link to="/about" className="inline-flex items-center justify-center rounded-md px-6 py-3 font-medium border border-white/40 hover:bg-white/10 transition-all duration-300" data-testid="banner-learn-btn">
                  How we do it
                </Link>
              </div>
            </div>

            {/* Right — visual flow */}
            <div className="relative">
              <div className="rounded-3xl bg-white/10 backdrop-blur-md border border-white/20 p-6 md:p-8">
                <p className="text-[11px] uppercase tracking-[0.25em] font-bold text-white/70 text-center mb-6">The Nayara way vs the usual chain</p>
                {/* Nayara flow */}
                <div className="rounded-2xl bg-white/10 border border-white/20 p-5" data-testid="flow-nayara">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex-1 text-center">
                      <div className="mx-auto w-14 h-14 rounded-2xl bg-white text-[var(--nayara-primary-hover)] flex items-center justify-center shadow-lg">
                        <Factory className="w-6 h-6" />
                      </div>
                      <div className="mt-2 text-xs font-semibold">Our Factory</div>
                      <div className="text-[10px] text-white/70">Jaito, Punjab</div>
                    </div>
                    <div className="flex flex-col items-center text-white/70">
                      <Truck className="w-5 h-5" />
                      <ArrowRight className="w-4 h-4" />
                    </div>
                    <div className="flex-1 text-center">
                      <div className="mx-auto w-14 h-14 rounded-2xl bg-white text-[var(--nayara-primary-hover)] flex items-center justify-center shadow-lg">
                        <HomeIcon className="w-6 h-6" />
                      </div>
                      <div className="mt-2 text-xs font-semibold">Your Home</div>
                      <div className="text-[10px] text-white/70">Anywhere in India</div>
                    </div>
                  </div>
                  <div className="mt-4 text-center">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white text-[var(--nayara-primary-hover)] text-[11px] font-bold">
                      <IndianRupee className="w-3 h-3" /> Real factory pricing
                    </span>
                  </div>
                </div>
                {/* Usual chain */}
                <div className="mt-5 rounded-2xl bg-black/15 border border-white/10 p-4 opacity-80" data-testid="flow-usual">
                  <div className="flex items-center justify-between gap-2 text-[10px] font-semibold text-white/80">
                    <span className="flex-1 text-center">Factory</span>
                    <ArrowRight className="w-3 h-3" />
                    <span className="flex-1 text-center line-through">Distributor</span>
                    <ArrowRight className="w-3 h-3" />
                    <span className="flex-1 text-center line-through">Wholesaler</span>
                    <ArrowRight className="w-3 h-3" />
                    <span className="flex-1 text-center line-through">Retailer</span>
                    <ArrowRight className="w-3 h-3" />
                    <span className="flex-1 text-center">You</span>
                  </div>
                  <div className="mt-2 flex items-center justify-center gap-1.5 text-[11px] text-white/80">
                    <X className="w-3.5 h-3.5" /> Every layer adds 8–12% markup
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Trust badges */}
          <div className="mt-14 grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="trust-badges">
            {[
              { icon: ShieldCheck, label: "100% Authentic", sub: "Straight from the line" },
              { icon: Award, label: "Made in India", sub: "Jaito, Punjab" },
              { icon: Truck, label: "Free shipping ₹499+", sub: "Pan-India delivery" },
              { icon: Package, label: "Easy returns", sub: "7-day hassle-free" },
            ].map((b, i) => (
              <div key={i} className="flex items-center gap-3 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 px-4 py-3" data-testid={`trust-badge-${i}`}>
                <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                  <b.icon className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-semibold truncate">{b.label}</div>
                  <div className="text-[11px] text-white/75 truncate">{b.sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURED PRODUCTS */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="flex items-end justify-between mb-10">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3">Bestsellers</p>
            <h2 className="font-heading text-3xl md:text-4xl font-medium tracking-tight">Loved by 10,000+ Indian homes</h2>
          </div>
          <Link to="/shop" className="hidden md:inline-flex items-center gap-1 text-sm font-medium text-[var(--nayara-primary)]">
            View All <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6" data-testid="featured-grid">
          {featured.map((p, i) => <ProductCard key={p.product_id} product={p} index={i} />)}
        </div>
      </section>

      {/* BRAND STORY (BENTO) */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 md:col-span-7 rounded-3xl overflow-hidden relative aspect-[16/10]">
            <img src="https://images.unsplash.com/photo-1681822520036-d84c2a1eefa4?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Njl8MHwxfHNlYXJjaHwyfHxmcmVzaCUyMGxhdW5kcnklMjBzdW5ueXxlbnwwfHx8fDE3NzY2ODM4NDh8MA&ixlib=rb-4.1.0&q=85" alt="Fresh laundry" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-tr from-[#0F172A]/60 to-transparent" />
            <div className="absolute bottom-6 left-6 right-6 text-white">
              <p className="text-xs uppercase tracking-[0.2em] font-bold mb-2 opacity-90">The Nayara promise</p>
              <h3 className="font-heading text-2xl md:text-3xl font-medium max-w-md">Clean that feels honest — from our factory to your home.</h3>
            </div>
          </div>
          <div className="col-span-12 md:col-span-5 grid grid-cols-1 gap-6">
            <div className="rounded-3xl bg-white border border-[var(--nayara-border)] p-8">
              <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3">Factory Direct Pricing</p>
              <h3 className="font-heading text-2xl font-medium">Up to 30% lower than shelf.</h3>
              <p className="mt-3 text-sm text-[#64748B] leading-relaxed">By skipping distributors, we pass the savings back to you without ever compromising on quality.</p>
            </div>
            <div className="rounded-3xl p-8 text-white" style={{ background: "var(--nayara-secondary)" }}>
              <p className="text-xs uppercase tracking-[0.2em] font-bold mb-3 opacity-80">Made in India</p>
              <h3 className="font-heading text-2xl font-medium">Proudly manufactured in Punjab.</h3>
              <p className="mt-3 text-sm opacity-90 leading-relaxed">Crafted in Jaito, District Faridkot — a small town in Punjab — by a team trained in small-batch methods that have served Indian households for years.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CATEGORIES */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3">Explore</p>
        <h2 className="font-heading text-3xl md:text-4xl font-medium tracking-tight mb-10">Shop by category</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { key: "laundry", label: "Laundry Care", img: "https://images.unsplash.com/photo-1582020711621-ab153a0f3631?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjV8MHwxfHNlYXJjaHwzfHxmcmVzaCUyMGNsZWFuaW5nJTIwcHJvZHVjdHN8ZW58MHx8fHwxNzc2NjgzODQ4fDA&ixlib=rb-4.1.0&q=85" },
            { key: "personal-care", label: "Personal Care", img: "https://images.unsplash.com/photo-1542038335240-86aea625b913?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzV8MHwxfHNlYXJjaHwyfHxtaW5pbWFsJTIwc29hcCUyMHBhY2thZ2luZ3xlbnwwfHx8fDE3NzY2ODM4Nzh8MA&ixlib=rb-4.1.0&q=85" },
            { key: "home-care", label: "Home Care", img: "https://images.pexels.com/photos/10566509/pexels-photo-10566509.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940" },
          ].map((c) => (
            <Link key={c.key} to={`/shop?category=${c.key}`} className="group relative rounded-3xl overflow-hidden aspect-[4/5]" data-testid={`category-${c.key}`}>
              <img src={c.img} alt={c.label} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              <div className="absolute inset-0 bg-gradient-to-t from-[#0F172A] via-[#0F172A]/30 to-transparent" />
              <div className="absolute bottom-6 left-6 right-6 text-white flex items-end justify-between">
                <h3 className="font-heading text-2xl font-medium">{c.label}</h3>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
