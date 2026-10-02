import React from "react";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { FieldError, describedBy } from "./FormErrors";

const LABEL = "text-xs font-bold uppercase tracking-[0.15em]";

/**
 * The seven fields a courier needs, typed the same way wherever they appear.
 *
 * Each input's id matches its field name so the error summary's links land on
 * the field they name. Only one of these may be on screen at a time for that
 * reason.
 */
export default function AddressFields({ address, onChange, fields = {} }) {
  const field = (name) => ({
    id: name,
    value: address[name] || "",
    onChange: onChange(name),
    "data-testid": `addr-${name}`,
    ...describedBy(name, { error: Boolean(fields[name]) }),
  });

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="md:col-span-2">
        <Label htmlFor="full_name" className={LABEL} required>Full name</Label>
        <Input {...field("full_name")} required />
        <FieldError name="full_name">{fields.full_name}</FieldError>
      </div>
      <div>
        <Label htmlFor="phone" className={LABEL} required>Phone</Label>
        <Input {...field("phone")} required />
        <FieldError name="phone">{fields.phone}</FieldError>
      </div>
      <div>
        <Label htmlFor="pincode" className={LABEL} required>PIN code</Label>
        <Input {...field("pincode")} required />
        <FieldError name="pincode">{fields.pincode}</FieldError>
      </div>
      <div className="md:col-span-2">
        <Label htmlFor="line1" className={LABEL} required>Address line 1</Label>
        <Input {...field("line1")} required />
        <FieldError name="line1">{fields.line1}</FieldError>
      </div>
      <div className="md:col-span-2">
        <Label htmlFor="line2" className={LABEL}>Address line 2</Label>
        <Input {...field("line2")} />
        <FieldError name="line2">{fields.line2}</FieldError>
      </div>
      <div>
        <Label htmlFor="city" className={LABEL} required>City</Label>
        <Input {...field("city")} required />
        <FieldError name="city">{fields.city}</FieldError>
      </div>
      <div>
        <Label htmlFor="state" className={LABEL} required>State</Label>
        <Input {...field("state")} required />
        <FieldError name="state">{fields.state}</FieldError>
      </div>
    </div>
  );
}
