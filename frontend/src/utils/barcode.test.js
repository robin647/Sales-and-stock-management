import assert from "node:assert/strict";
import test from "node:test";
import { barcodeFitsLabel, encodeProductBarcode, productLabelPrice } from "./barcode.js";

test("Code 128 has start/stop patterns and ten-module quiet zones", () => {
  const barcode = encodeProductBarcode("MS-000123");
  assert.equal(barcode.modules, 132);
  const bits = Array(barcode.modules).fill("0");
  barcode.bars.forEach(bar => {
    assert.ok(bar.width > 0);
    assert.ok(bar.x >= 10 && bar.x + bar.width <= barcode.modules - 10);
    bits.fill("1", bar.x, bar.x + bar.width);
  });
  const encoded = bits.slice(10, -10).join("");
  assert.ok(encoded.startsWith("11010010000"));
  assert.ok(encoded.endsWith("1100011101011"));
  assert.ok(barcodeFitsLabel(barcode, 50));
});

test("missing and non-ASCII codes are rejected instead of printing invalid bars", () => {
  assert.throws(() => encodeProductBarcode(""), /missing/);
  assert.throws(() => encodeProductBarcode("পাঞ্জাবি"), /English/);
});

test("labels too narrow for a long code are rejected", () => {
  const barcode = encodeProductBarcode("A".repeat(64));
  assert.equal(barcodeFitsLabel(barcode, 50), false);
});

test("label uses discounted price when present and otherwise sale price", () => {
  assert.equal(productLabelPrice({ selling_price: "5000", discount_price: "4250" }), 4250);
  assert.equal(productLabelPrice({ selling_price: "5000", discount_price: null }), 5000);
});
