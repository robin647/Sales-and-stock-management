const bengaliDigits = "০১২৩৪৫৬৭৮৯";
const invoiceLabel = /\bInvoice\b(?:[ \t]+(?:Number\b|No\b\.?))?[ \t:#.=\-]*/i;
const codLabel = /\b(?:Total[ \t]+)?(?:Cash[ \t-]+on[ \t-]+Delivery|C\.?[ \t]*O\.?[ \t]*D)\b\.?(?:[ \t]+(?:Total(?:[ \t]+Amount)?|Amount))?\b/i;
const labelSeparator = /^[ \t:#.=]*(?:-[ \t]+)?/;
const invoiceValue = /^([\w][\w/-]{0,63})(?=$|[ \t|;])/;
// OCR sometimes reads the taka symbol as a single digit before the amount.
const amountValue = /^(?:[৳$]|(?:BDT|Tk\.?|Taka)(?=\s|\d)|টাকা|\d(?=[ \t]+\d(?:\d|,\d)))?[ \t]*(\d+(?:,\d{2,3})*(?:\.\d{1,2})?)(?=$|[ \t|;৳]|\/-)/i;

function readLabeledValue(lines, label, valuePattern, allowTextOnNextLine = false) {
  for (const [index, line] of lines.entries()) {
    const match = line.match(label);
    if (!match) continue;
    const inline = line.slice(match.index + match[0].length).replace(labelSeparator, "");
    const nextLine = lines[index + 1] || "";
    const value = inline
      ? inline.match(valuePattern)?.[1]
      : nextLine.match(valuePattern)?.[1];
    if (value && (inline || allowTextOnNextLine || /\d/.test(value))) return value;
  }
  return "";
}

export function parseCourierLabel(text) {
  const normalized = text
    .normalize("NFKC")
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
      if (/^(?:Area\b|Printed\b|[৳$])/i.test(line) || line.search(codLabel) === 0 || line.search(invoiceLabel) === 0) break;
      address.push(line);
    }
  }
  const tracking = normalized.match(/\bS\s*F\s*[-_.]?\s*I\s*D\s*[:.-]?\s*(\d{6,})/i)?.[1];
  const amount = readLabeledValue(lines, codLabel, amountValue);
  const phone = field(/^Phone\b\s*[:.-]?\s*/i).match(/\+?\d[\d -]{7,}\d/)?.[0];
  const weight = readLabeledValue(
    lines, /^(?:[^\p{L}\d]*?)Weight\b/iu, /^(\d+(?:[.,]\d{1,2})?(?:\s*(?:kg|g|কেজি|গ্রাম))?)(?=$|[|;]|\s+(?![a-z]))/i,
  );
  const weightNumber = Number.parseFloat(weight.replace(",", "."));
  const weightKg = /(?:^|[\d\s])(?:g|গ্রাম)$/i.test(weight) ? weightNumber / 1000 : weightNumber;
  const delivery = readLabeledValue(lines, /^Delivery\b/i, /^(Home|Point)\b/i, true);

  return {
    tracking_id: tracking || lines.find((line) => /^\d{8,}$/.test(line)) || "",
    invoice: readLabeledValue(lines, invoiceLabel, invoiceValue),
    customer_name: field(/^Name\b\s*[:.-]?\s*/i),
    phone: phone?.replace(/[ -]/g, "") || "",
    address: address.filter(Boolean).join(" "),
    area: field(/^Area\b\s*[:.-]?\s*/i),
    quantity: field(/^(?:Quantity|Qty|Items)\b\s*[:.-]?\s*/i).match(/^\d+\b/)?.[0] || "",
    cod_amount: amount.replace(/,/g, ""),
    weight_kg: weightKg >= 0.01 && weightKg <= 600 ? String(Math.round(weightKg * 100) / 100) : "",
    courier_delivery: delivery.toLowerCase(),
  };
}
