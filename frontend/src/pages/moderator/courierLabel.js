const bengaliDigits = "০১২৩৪৫৬৭৮৯";

export function parseCourierLabel(text) {
  const normalized = text
    .replace(/[০-৯]/g, (digit) => String(bengaliDigits.indexOf(digit)))
    .replace(/[–—]/g, "-");
  const lines = normalized.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const field = (label) => lines.find((line) => label.test(line))?.replace(label, "").trim() || "";
  const addressLabel = /^Address\b\s*[:.-]?\s*/i;
  const addressIndex = lines.findIndex((line) => addressLabel.test(line));
  const address = [];
  if (addressIndex >= 0) {
    address.push(lines[addressIndex].replace(addressLabel, ""));
    for (const line of lines.slice(addressIndex + 1)) {
      if (/^(?:Area|Cash\s+on\s+Delivery|COD\b|Printed\b|[৳$])/i.test(line)) break;
      address.push(line);
    }
  }
  const tracking = normalized.match(/\bS\s*F\s*[-_.]?\s*I\s*D\s*[:.-]?\s*(\d{6,})/i)?.[1];
  const amount = normalized.match(/(?:Cash\s+on\s+Delivery|\bCOD\b)[^\d\r\n]*?(\d[\d,]*(?:\.\d{1,2})?)/i)?.[1];
  const phone = field(/^Phone\b\s*[:.-]?\s*/i).match(/\+?\d[\d -]{7,}\d/)?.[0];

  return {
    tracking_id: tracking || lines.find((line) => /^\d{8,}$/.test(line)) || "",
    invoice: normalized.match(/\bInvoice[ \t.:\-]+([\w-]+)[ \t]*$/im)?.[1] || "",
    customer_name: field(/^Name\b\s*[:.-]?\s*/i),
    phone: phone?.replace(/[ -]/g, "") || "",
    address: address.filter(Boolean).join(" "),
    area: field(/^Area\b\s*[:.-]?\s*/i),
    quantity: field(/^(?:Quantity|Qty|Items)\b\s*[:.-]?\s*/i).match(/^\d+\b/)?.[0] || "",
    cod_amount: amount?.replace(/,/g, "") || "",
  };
}
