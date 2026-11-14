import JsBarcode from "jsbarcode";

export function encodeProductBarcode(value) {
  const code = String(value ?? "").trim();
  if (!code) throw new Error("Product code is missing. Save this product after deploying the updated backend.");
  if (!/^[\x20-\x7E]{1,64}$/.test(code)) throw new Error("Use a product code with English letters, numbers or printable symbols (up to 64 characters).");
  const data = {};
  JsBarcode(data, code, { format: "CODE128", displayValue: false });
  const pattern = data.encodings.map(encoding => encoding.data).join("");
  const bars = [];
  for (let index = 0; index < pattern.length;) {
    if (pattern[index] !== "1") { index++; continue; }
    const start = index;
    while (pattern[index] === "1") index++;
    bars.push({ x: start + 10, width: index - start });
  }
  return { code, bars, modules: pattern.length + 20 };
}

export function barcodeFitsLabel(barcode, widthMm) {
  return (widthMm - 4) / barcode.modules >= 0.19;
}

export function productLabelPrice(product) {
  return Number(product.discount_price ?? product.selling_price ?? 0);
}
