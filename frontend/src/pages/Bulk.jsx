import React, { useState } from "react";
import { Factory, TrendingUp, BadgeCheck, Truck, ShieldCheck, MapPin, Briefcase, Check, Package, ArrowRight } from "lucide-react";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Checkbox } from "../components/ui/checkbox";
import RequiredMark from "../components/RequiredMark";
import { api } from "../lib/api";
import { BUSINESS } from "../lib/business";
import { toast } from "sonner";

const BENEFITS = [
  { icon: Factory, title: "Factory Direct Supply", desc: "Skip distributors — source straight from our Punjab manufacturing unit." },
  { icon: TrendingUp, title: "Better Margins", desc: "Bulk pricing engineered to protect your retail margins, every time." },
  { icon: BadgeCheck, title: "Consistent Quality", desc: "Batch-tested formulations that keep your customers coming back." },
  { icon: Truck, title: "Reliable Bulk Delivery", desc: "Pan-India logistics with dedicated coordinators for large orders." },
  { icon: MapPin, title: "Made in India", desc: "Crafted in Jaito, Faridkot — built for Indian water, skin, and weather." },
];

const CATEGORIES = [
  { icon: Package, title: "Laundry Products", items: ["Washing Soap Bars", "Detergent Powders", "Liquid Detergents"] },
  { icon: ShieldCheck, title: "Handwash & Personal Care", items: ["Handwash Liquids", "Handwash Bars", "Bathing Soaps"] },
  { icon: Truck, title: "Bathroom Cleaning", items: ["Toilet Cleaners", "Surface Cleaners", "Disinfectants"] },
];

const PRODUCT_OPTIONS = [
  "Washing Soap Bars",
  "Washing Powder Detergent",
  "Liquid Detergents",
  "Handwash Soap Bars",
  "Handwash Liquids",
  "Bathing Soaps",
  "Toilet Cleaners",
  "Surface Cleaners",
];

export default function Bulk() {
  const [form, setForm] = useState({
    name: "",
    business_name: "",
    phone: "",
    email: "",
    city: "",
    products_interested: [],
    quantity: "",
    message: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const toggleProduct = (p) => {
    setForm((f) => ({
      ...f,
      products_interested: f.products_interested.includes(p)
        ? f.products_interested.filter((x) => x !== p)
        : [...f.products_interested, p],
    }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/bulk-inquiry", form);
      setSubmitted(true);
      window.scrollTo({ top: document.getElementById("inquiry")?.offsetTop - 80, behavior: "smooth" });
    } catch {
      toast.error("Could not submit inquiry. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-testid="bulk-page">
      {/* HERO */}
      <section className="relative overflow-hidden border-b border-[var(--nayara-border)]">
        <div className="absolute inset-0 bg-gradient-to-br from-[#FBEEE4] via-white to-[#E6F0F9]" />
        <div className="relative max-w-7xl mx-auto px-6 py-20 lg:py-28">
          <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-12 items-center">
            <div>
              <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold badge-soft-blue">
                <Briefcase className="w-3.5 h-3.5" /> For Retailers · Wholesalers · Distributors
              </span>
              <h1 className="mt-5 font-heading text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tighter leading-[1.05]" data-testid="bulk-hero-headline">
                Bulk Orders &<br />Business Partnerships.
              </h1>
              <p className="mt-6 text-base md:text-lg text-[#64748B] max-w-xl leading-relaxed">
                Get factory-direct pricing and reliable supply for your business needs. No distributors, no mark-ups — just straight-from-the-line economics built for your margins.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <a href="#inquiry" className="nayara-btn" data-testid="bulk-hero-cta">
                  Request Bulk Pricing <ArrowRight className="w-4 h-4 ml-2" />
                </a>
                <a href={BUSINESS.phoneHref} className="nayara-btn-outline" data-testid="bulk-hero-call">
                  Or call {BUSINESS.phone}
                </a>
              </div>
              <div className="mt-8 flex flex-wrap items-center gap-5 text-sm text-[#64748B]">
                <div className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-[var(--nayara-primary)]" /> Competitive bulk pricing</div>
                <div className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-[var(--nayara-primary)]" /> Custom quote in 24 hours</div>
                <div className="flex items-center gap-1.5"><Check className="w-3.5 h-3.5 text-[var(--nayara-primary)]" /> Flexible packaging</div>
              </div>
            </div>
            <div className="relative hidden lg:block">
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-3xl bg-white border border-[var(--nayara-border)] p-6 col-span-2">
                  <Factory className="w-6 h-6 text-[var(--nayara-primary)] mb-3" />
                  <div className="font-heading text-2xl font-medium">46 years</div>
                  <div className="text-xs text-[#64748B]">of manufacturing expertise in Jaito, Punjab</div>
                </div>
                <div className="rounded-3xl p-6 text-white" style={{ background: "var(--nayara-primary)" }}>
                  <TrendingUp className="w-6 h-6 mb-3" />
                  <div className="font-heading text-2xl font-medium">Up to 30%</div>
                  <div className="text-xs opacity-90">better margins for partners</div>
                </div>
                <div className="rounded-3xl p-6 text-white" style={{ background: "var(--nayara-secondary)" }}>
                  <Truck className="w-6 h-6 mb-3" />
                  <div className="font-heading text-2xl font-medium">Pan-India</div>
                  <div className="text-xs opacity-90">bulk delivery network</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* WHY PARTNER */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3">Why Partner with Nayara</p>
          <h2 className="font-heading text-2xl md:text-3xl font-medium tracking-tight">Built for businesses that move volume.</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="bulk-benefits">
          {BENEFITS.map((b, i) => (
            <div key={i} className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 hover:shadow-md transition">
              <div className="w-11 h-11 rounded-xl bg-[#FBEEE4] text-[var(--nayara-primary-hover)] flex items-center justify-center">
                <b.icon className="w-5 h-5" />
              </div>
              <h3 className="font-heading font-semibold text-lg mt-4">{b.title}</h3>
              <p className="text-sm text-[#64748B] mt-2 leading-relaxed">{b.desc}</p>
            </div>
          ))}
          <div className="rounded-2xl border border-dashed border-[var(--nayara-border)] bg-[#FBEEE4]/40 p-6 flex items-center">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] font-bold text-[var(--nayara-primary-hover)] mb-2">Partner perk</p>
              <p className="text-sm text-[#64748B] leading-relaxed">Dedicated account manager, priority fulfilment, and early access to new product lines.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CATEGORIES */}
      <section className="bg-[#FAFAFA] border-y border-[var(--nayara-border)]">
        <div className="max-w-7xl mx-auto px-6 py-20">
          <div className="mb-10">
            <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3">Our Range</p>
            <h2 className="font-heading text-2xl md:text-3xl font-medium tracking-tight">Available in bulk — across our full catalogue.</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5" data-testid="bulk-categories">
            {CATEGORIES.map((c, i) => (
              <div key={i} className="rounded-2xl bg-white border border-[var(--nayara-border)] p-6">
                <div className="w-11 h-11 rounded-xl bg-[#E6F0F9] text-[var(--nayara-secondary)] flex items-center justify-center">
                  <c.icon className="w-5 h-5" />
                </div>
                <h3 className="font-heading font-semibold text-lg mt-4">{c.title}</h3>
                <ul className="mt-4 space-y-2">
                  {c.items.map((it) => (
                    <li key={it} className="flex items-center gap-2 text-sm text-[#64748B]">
                      <Check className="w-4 h-4 text-[var(--nayara-primary)] flex-shrink-0" /> {it}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="mt-8 rounded-xl bg-white border border-[var(--nayara-border)] px-6 py-4 flex items-start gap-3">
            <BadgeCheck className="w-5 h-5 text-[var(--nayara-primary)] flex-shrink-0 mt-0.5" />
            <div className="text-sm text-[#64748B]">
              Available in bulk quantities with <span className="font-semibold text-[#0F172A]">flexible packaging sizes</span> — choose the pack size that fits your channel.
            </div>
          </div>
          <div className="mt-4 rounded-xl bg-[#E6F0F9] border border-[#CDE0F0] px-6 py-4 text-sm text-[var(--nayara-secondary)]">
            <span className="font-semibold">Competitive bulk pricing shared on inquiry.</span> Customized quotes based on quantity and packaging requirements.
          </div>
        </div>
      </section>

      {/* INQUIRY FORM */}
      <section id="inquiry" className="max-w-5xl mx-auto px-6 py-20 scroll-mt-24">
        <div className="text-center mb-10">
          <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3">Get Your Quote</p>
          <h2 className="font-heading text-2xl md:text-3xl font-medium tracking-tight">Tell us what you need.</h2>
          <p className="mt-3 text-[#64748B] max-w-lg mx-auto">We respond to every inquiry within 24 business hours with a customized quote.</p>
        </div>

        {submitted ? (
          <div className="rounded-3xl border border-[var(--nayara-border)] bg-white p-10 text-center" data-testid="bulk-submit-success">
            <div className="mx-auto w-16 h-16 rounded-full flex items-center justify-center text-white mb-5" style={{ background: "var(--nayara-primary)" }}>
              <Check className="w-8 h-8" />
            </div>
            <h3 className="font-heading text-2xl font-medium">Inquiry received!</h3>
            <p className="mt-3 text-[#64748B] max-w-md mx-auto">Thank you. Our business team will reach out to you within 24 hours at the phone/email you shared.</p>
            <button onClick={() => { setSubmitted(false); setForm({ name: "", business_name: "", phone: "", email: "", city: "", products_interested: [], quantity: "", message: "" }); }} className="nayara-btn-outline mt-6" data-testid="bulk-submit-another">
              Submit another inquiry
            </button>
          </div>
        ) : (
          <form onSubmit={submit} className="rounded-3xl border border-[var(--nayara-border)] bg-white p-8 md:p-10 space-y-6" data-testid="bulk-inquiry-form">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label htmlFor="name" className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-2 block">Your Name<RequiredMark /></label>
                <Input id="name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="bulk-name" />
              </div>
              <div>
                <label htmlFor="business_name" className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-2 block">Business Name<RequiredMark /></label>
                <Input id="business_name" required value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} data-testid="bulk-business" />
              </div>
              <div>
                <label htmlFor="phone" className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-2 block">Phone Number<RequiredMark /></label>
                <Input id="phone" required type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="bulk-phone" />
              </div>
              <div>
                <label htmlFor="email" className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-2 block">Email<RequiredMark /></label>
                <Input id="email" required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="bulk-email" />
              </div>
              <div>
                <label htmlFor="city" className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-2 block">City / Location<RequiredMark /></label>
                <Input id="city" required value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} data-testid="bulk-city" />
              </div>
              <div>
                <label htmlFor="quantity" className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-2 block">Quantity Required<RequiredMark /></label>
                <Input id="quantity" required placeholder="e.g. 500 kg / 1000 units / monthly" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} data-testid="bulk-quantity" />
              </div>
            </div>

            <fieldset>
              {/* A set of checkboxes is one question, so it is grouped and the
                  heading is its legend rather than a label for any one box. */}
              <legend className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-3 block">Products Interested In</legend>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2" data-testid="bulk-products">
                {PRODUCT_OPTIONS.map((p) => (
                  <label key={p} className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm cursor-pointer transition ${form.products_interested.includes(p) ? "border-[var(--nayara-primary)] bg-[#FBEEE4]" : "border-[var(--nayara-border)] hover:border-[var(--nayara-primary)]"}`}>
                    <Checkbox checked={form.products_interested.includes(p)} onCheckedChange={() => toggleProduct(p)} data-testid={`bulk-product-${p.toLowerCase().replace(/\s+/g, '-')}`} />
                    <span>{p}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <div>
              <label htmlFor="message" className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-2 block">Message / Requirements</label>
              <Textarea id="message" rows={4} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Share any specific requirements — packaging, delivery location, timelines, private labelling, etc." data-testid="bulk-message" />
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-[var(--nayara-border)]">
              <p className="text-xs text-[#64748B]">By submitting, you agree to be contacted by Nayara's business team.</p>
              <button type="submit" disabled={submitting} className="nayara-btn w-full sm:w-auto" data-testid="bulk-submit-btn">
                {submitting ? "Submitting..." : "Submit Inquiry"} <ArrowRight className="w-4 h-4 ml-2" />
              </button>
            </div>
          </form>
        )}
      </section>

      {/* TRUST SECTION */}
      <section className="bg-[#0F172A] text-white">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8" data-testid="bulk-trust">
            <div>
              <Factory className="w-6 h-6 text-[var(--nayara-primary)] mb-3" />
              <h3 className="font-heading text-lg font-semibold">Trusted manufacturing</h3>
              <p className="text-sm text-white/70 mt-2 leading-relaxed">Four decades of consistent batch production with in-house QC labs and ISO-grade processes.</p>
            </div>
            <div>
              <Truck className="w-6 h-6 text-[var(--nayara-accent)] mb-3" />
              <h3 className="font-heading text-lg font-semibold">Direct from factory</h3>
              <p className="text-sm text-white/70 mt-2 leading-relaxed">No middle layer. Orders ship straight from our Jaito plant — shorter lead times, better prices.</p>
            </div>
            <div>
              <MapPin className="w-6 h-6 text-[var(--nayara-primary)] mb-3" />
              <h3 className="font-heading text-lg font-semibold">Built for Indian markets</h3>
              <p className="text-sm text-white/70 mt-2 leading-relaxed">Formulations tuned for Indian water hardness, skin profiles, and retail price sensitivity.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
