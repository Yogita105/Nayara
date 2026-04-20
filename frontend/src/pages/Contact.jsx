import React, { useState } from "react";
import { Mail, Phone, MapPin, Send } from "lucide-react";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Button } from "../components/ui/button";
import { api } from "../lib/api";
import { toast } from "sonner";

export default function Contact() {
  const [form, setForm] = useState({ name: "", email: "", phone: "", subject: "", message: "" });
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/contact", form);
      toast.success("Message sent! We'll get back to you soon.");
      setForm({ name: "", email: "", phone: "", subject: "", message: "" });
    } catch { toast.error("Could not send message"); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-14" data-testid="contact-page">
      <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3">Contact</p>
      <h1 className="font-heading text-4xl md:text-5xl font-medium tracking-tighter mb-4">Let's talk.</h1>
      <p className="text-[#64748B] max-w-xl">Questions about a product, bulk order or wholesale? Our team responds within 24 hours.</p>

      <div className="mt-12 grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-10">
        <form onSubmit={submit} className="rounded-3xl border border-[var(--nayara-border)] bg-white p-8 space-y-4" data-testid="contact-form">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-2 block">Name</label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required data-testid="contact-name" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-2 block">Email</label>
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required data-testid="contact-email" />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-2 block">Phone</label>
              <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="contact-phone" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-2 block">Subject</label>
              <Input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} required data-testid="contact-subject" />
            </div>
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-2 block">Message</label>
            <Textarea value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} rows={6} required data-testid="contact-message" />
          </div>
          <Button type="submit" disabled={submitting} className="w-full bg-[var(--nayara-primary)] hover:bg-[var(--nayara-primary-hover)]" data-testid="contact-submit">
            <Send className="w-4 h-4 mr-2" /> {submitting ? "Sending..." : "Send Message"}
          </Button>
        </form>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            <MapPin className="w-5 h-5 text-[var(--nayara-primary)] mb-2" />
            <h3 className="font-heading font-semibold">Visit us</h3>
            <p className="text-sm text-[#64748B] mt-1">Jaito, District Faridkot,<br />Punjab 151202, India</p>
          </div>
          <div className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            <Phone className="w-5 h-5 text-[var(--nayara-primary)] mb-2" />
            <h3 className="font-heading font-semibold">Call us</h3>
            <p className="text-sm text-[#64748B] mt-1">Abhinav Grover (Owner)<br />+91 97808 44330<br />Mon–Sat · 10am–7pm</p>
          </div>
          <div className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            <Mail className="w-5 h-5 text-[var(--nayara-primary)] mb-2" />
            <h3 className="font-heading font-semibold">Email us</h3>
            <p className="text-sm text-[#64748B] mt-1">hello@nayara.in<br />wholesale@nayara.in</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
