import React from "react";
import { Link } from "react-router-dom";
import { Leaf, MapPin, Mail, Phone } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-[var(--nayara-border)] bg-white mt-20" data-testid="site-footer">
      <div className="max-w-7xl mx-auto px-6 py-14 grid grid-cols-1 md:grid-cols-4 gap-10">
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-9 h-9 rounded-full flex items-center justify-center text-white font-bold" style={{ background: "var(--nayara-primary)" }}>N</div>
            <span className="font-heading text-2xl font-semibold">Nayara</span>
          </div>
          <p className="text-sm text-[#5C7671] leading-relaxed">
            Premium cleaning & personal care crafted in small batches — delivered factory direct to Indian households.
          </p>
          <div className="flex items-center gap-2 mt-5 text-xs badge-soft px-3 py-1.5 rounded-full w-fit">
            <Leaf className="w-3 h-3" /> Made in India · Factory Direct
          </div>
        </div>

        <div>
          <h4 className="font-heading font-semibold mb-4">Shop</h4>
          <ul className="space-y-2 text-sm text-[#5C7671]">
            <li><Link to="/shop?category=laundry" className="hover:text-[var(--nayara-primary)]">Laundry Care</Link></li>
            <li><Link to="/shop?category=personal-care" className="hover:text-[var(--nayara-primary)]">Personal Care</Link></li>
            <li><Link to="/shop?category=home-care" className="hover:text-[var(--nayara-primary)]">Home Care</Link></li>
            <li><Link to="/shop" className="hover:text-[var(--nayara-primary)]">All Products</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="font-heading font-semibold mb-4">Company</h4>
          <ul className="space-y-2 text-sm text-[#5C7671]">
            <li><Link to="/about" className="hover:text-[var(--nayara-primary)]">About Us</Link></li>
            <li><Link to="/contact" className="hover:text-[var(--nayara-primary)]">Contact</Link></li>
            <li><Link to="/orders" className="hover:text-[var(--nayara-primary)]">Track Order</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="font-heading font-semibold mb-4">Reach Us</h4>
          <ul className="space-y-3 text-sm text-[#5C7671]">
            <li className="flex items-start gap-2"><MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" /> Industrial Estate, Pune 411019, India</li>
            <li className="flex items-center gap-2"><Phone className="w-4 h-4" /> +91 98765 43210</li>
            <li className="flex items-center gap-2"><Mail className="w-4 h-4" /> hello@nayara.in</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-[var(--nayara-border)]">
        <div className="max-w-7xl mx-auto px-6 py-5 flex flex-col sm:flex-row items-center justify-between text-xs text-[#5C7671]">
          <p>© {new Date().getFullYear()} Nayara Brands Pvt. Ltd. All rights reserved.</p>
          <p className="mt-2 sm:mt-0">Crafted with care in Pune, India.</p>
        </div>
      </div>
    </footer>
  );
}
