import assert from "node:assert/strict";
import test from "node:test";
import { parseCourierLabel } from "./courierLabel.js";

test("imports a courier label without guessing quantity from the invoice", () => {
  assert.deepEqual(parseCourierLabel(`
    120000001
    Invoice 8
    SF-ID 120000001
    Name Sample Customer
    Phone 01000000000
    Address Apartment 2, Sample Road
      Sample Junction
    Area Dhaka
    Cash on Delivery ৳ 2,994.50
    Printed: 14/11/26
  `), {
    tracking_id: "120000001", invoice: "8", customer_name: "Sample Customer",
    phone: "01000000000", address: "Apartment 2, Sample Road Sample Junction",
    area: "Dhaka", quantity: "", cod_amount: "2994.50",
  });
});

test("reads explicit quantities and keeps a missing COD amount blank", () => {
  const result = parseCourierLabel("১২৩৪৫৬৭৮\nQuantity: ৩\nCash on Delivery\nPrinted: ১৪/১১/২৬");
  assert.equal(result.tracking_id, "12345678");
  assert.equal(result.quantity, "3");
  assert.equal(result.cod_amount, "");
});
