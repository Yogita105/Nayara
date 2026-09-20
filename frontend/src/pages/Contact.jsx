import React, { useState } from "react";
import { Mail, Phone, MapPin, Send } from "lucide-react";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Button } from "../components/ui/button";
import RequiredMark from "../components/RequiredMark";
import { ErrorSummary, FieldError, describedBy } from "../components/FormErrors";
import { api, errorMessage, fieldErrors } from "../lib/api";
import { toast } from "sonner";

const LABEL = "text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-2 block";
const EMPTY = { name: "", email: "", phone: "", subject: "", message: "" };

export default function Contact() {
  const [form, setForm] = useState(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [fields, setFields] = useState({});

  const update = (name) => (event) => {
    const { value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setFields((current) => {
      if (!current[name]) return current;
      const next = { ...current };
      delete next[name];
      return next;
    });
  };

  const findProblems = () => {
    const problems = {};
    if (form.name.trim().length < 2) {
      problems.name = "Enter your name, using at least 2 characters.";
    }
    if (!form.email.trim()) problems.email = "Enter an email address we can reply to.";
    if (!form.subject.trim()) problems.subject = "Enter a subject.";
    if (!form.message.trim()) problems.message = "Enter your message.";
    return problems;
  };

  const submit = async (event) => {
    event.preventDefault();
    const problems = findProblems();
    if (Object.keys(problems).length > 0) {
      setError("");
      setFields(problems);
      return;
    }

    setSubmitting(true);
    setError("");
    setFields({});
    try {
      await api.post("/contact", form);
      toast.success("Message sent! We'll get back to you soon.");
      setForm(EMPTY);
    } catch (requestError) {
      setError(errorMessage(requestError, "Could not send your message."));
      setFields(fieldErrors(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-14" data-testid="contact-page">
      <p className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B] mb-3">Contact</p>
      <h1 className="font-heading text-2xl md:text-3xl font-medium tracking-tighter mb-4">Let's talk.</h1>
      <p className="text-[#64748B] max-w-xl">Questions about a product, bulk order or wholesale? Our team responds within 24 hours.</p>

      <div className="mt-12 grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-10">
        <form onSubmit={submit} className="rounded-3xl border border-[var(--nayara-border)] bg-white p-8 space-y-4" data-testid="contact-form" noValidate>
          <ErrorSummary message={error} fields={fields} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="name" className={LABEL}>Name<RequiredMark /></label>
              <Input
                id="name"
                value={form.name}
                onChange={update("name")}
                autoComplete="name"
                required
                data-testid="contact-name"
                {...describedBy("name", { error: Boolean(fields.name) })}
              />
              <FieldError name="name">{fields.name}</FieldError>
            </div>
            <div>
              <label htmlFor="email" className={LABEL}>Email<RequiredMark /></label>
              <Input
                id="email"
                type="email"
                value={form.email}
                onChange={update("email")}
                autoComplete="email"
                required
                data-testid="contact-email"
                {...describedBy("email", { error: Boolean(fields.email) })}
              />
              <FieldError name="email">{fields.email}</FieldError>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="phone" className={LABEL}>Phone</label>
              <Input
                id="phone"
                type="tel"
                value={form.phone}
                onChange={update("phone")}
                autoComplete="tel"
                data-testid="contact-phone"
                {...describedBy("phone", { error: Boolean(fields.phone) })}
              />
              <FieldError name="phone">{fields.phone}</FieldError>
            </div>
            <div>
              <label htmlFor="subject" className={LABEL}>Subject<RequiredMark /></label>
              <Input
                id="subject"
                value={form.subject}
                onChange={update("subject")}
                required
                data-testid="contact-subject"
                {...describedBy("subject", { error: Boolean(fields.subject) })}
              />
              <FieldError name="subject">{fields.subject}</FieldError>
            </div>
          </div>
          <div>
            <label htmlFor="message" className={LABEL}>Message<RequiredMark /></label>
            <Textarea
              id="message"
              value={form.message}
              onChange={update("message")}
              rows={6}
              required
              data-testid="contact-message"
              {...describedBy("message", { error: Boolean(fields.message) })}
            />
            <FieldError name="message">{fields.message}</FieldError>
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
