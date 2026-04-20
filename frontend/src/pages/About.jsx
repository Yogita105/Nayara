import React from "react";
import { Leaf, Factory, Heart, Users } from "lucide-react";

export default function About() {
  return (
    <div data-testid="about-page">
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[#E8F1F2] to-[#F8F9FA]" />
        <div className="relative max-w-5xl mx-auto px-6 py-20 text-center">
          <span className="badge-soft px-4 py-1.5 rounded-full text-xs font-semibold inline-flex items-center gap-1.5">
            <Leaf className="w-3.5 h-3.5" /> Our Story
          </span>
          <h1 className="mt-6 font-heading text-4xl md:text-6xl font-medium tracking-tighter leading-[1.05]">
            Three generations of honest clean.
          </h1>
          <p className="mt-6 text-[#5C7671] max-w-2xl mx-auto leading-relaxed">
            Nayara began in a small workshop in Jaito, Punjab, when founder Abhinav Grover mixed his first batch of neem-infused laundry soap. Today, the same recipes live on — made with the same care, direct from our factory to your door.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
        <img src="https://images.unsplash.com/photo-1681822520036-d84c2a1eefa4?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Njl8MHwxfHNlYXJjaHwyfHxmcmVzaCUyMGxhdW5kcnklMjBzdW5ueXxlbnwwfHx8fDE3NzY2ODM4NDh8MA&ixlib=rb-4.1.0&q=85" alt="Laundry in sunlight" className="rounded-3xl object-cover w-full aspect-[4/5]" />
        <div>
          <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#5C7671] mb-3">Why Nayara</p>
          <h2 className="font-heading text-3xl md:text-4xl font-medium mb-5 tracking-tight">Real ingredients. Real value.</h2>
          <p className="text-[#5C7671] leading-relaxed mb-4">
            Every Nayara formula is developed by a team of chemists and tested in real Indian homes — washing saris, school uniforms, steel dabbas, and everything in between.
          </p>
          <p className="text-[#5C7671] leading-relaxed">
            By going factory-direct we cut out four middlemen and pass the savings back to you — without ever cutting corners on quality, purity, or safety.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          {[
            { icon: Factory, stat: "46", label: "Years in manufacturing" },
            { icon: Heart, stat: "10K+", label: "Homes served" },
            { icon: Users, stat: "120", label: "Craftspeople employed" },
            { icon: Leaf, stat: "100%", label: "Made in India" },
          ].map((s, i) => (
            <div key={i} className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 text-center">
              <s.icon className="w-6 h-6 mx-auto mb-3 text-[var(--nayara-primary)]" />
              <div className="font-heading text-3xl font-semibold">{s.stat}</div>
              <div className="text-sm text-[#5C7671] mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="rounded-3xl p-10 md:p-16 text-white text-center" style={{ background: "var(--nayara-primary)" }}>
          <h2 className="font-heading text-3xl md:text-4xl font-medium">"Clean, for us, has always meant honest."</h2>
          <p className="mt-4 opacity-90">— Nayara family, since 1978</p>
        </div>
      </section>
    </div>
  );
}
