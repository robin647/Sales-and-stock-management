import assert from "node:assert/strict";
import test from "node:test";
import { parseCourierLabel } from "./courierLabel.js";
import { courierPdfText } from "./courierPdfText.js";
import { suggestDeliveryZone } from "./deliveryZone.js";
import { suggestSteadfastDestination } from "./steadfastDistrict.js";

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
    area: "Dhaka", quantity: "", cod_amount: "2994.50", weight_kg: "", courier_delivery: "",
  });
});

test("pairs far-apart PDF label columns and the larger COD text", () => {
  const item = (str, x, y) => ({ str, transform: [1, 0, 0, 1, x, y] });
  const result = parseCourierLabel(courierPdfText([
    item("3", 425, 629), item("Invoice", 256, 629),
    item("Delivery", 256, 601), item("Home", 405, 601),
    item("Weight", 256, 587), item("1.5 KG", 403, 587),
    item("Area", 182, 509), item("Dinajpur Sadar, Dinajpur", 227, 509),
    item("Cash on Delivery", 191, 480), item("৳", 372, 479), item("2,394", 385, 479),
  ]));
  assert.equal(result.invoice, "3");
  assert.equal(result.cod_amount, "2394");
  assert.equal(result.weight_kg, "1.5");
  assert.equal(result.courier_delivery, "home");
  assert.equal(suggestSteadfastDestination(result.address, result.area), "15");
  assert.equal(suggestSteadfastDestination("", "দিনাজপুর সদর, দিনাজপুর"), "15");
  assert.equal(suggestSteadfastDestination("", "মিরপুর, ঢাকা"), "1");
  assert.equal(parseCourierLabel("Weight:\n750 g").weight_kg, "0.75");
});

test("reads explicit quantities and keeps a missing COD amount blank", () => {
  const result = parseCourierLabel("১২৩৪৫৬৭৮\nQuantity: ৩\nCash on Delivery\nPrinted: ১৪/১১/২৬");
  assert.equal(result.tracking_id, "12345678");
  assert.equal(result.quantity, "3");
  assert.equal(result.cod_amount, "");
});

test("reads the black COD box when OCR mistakes the taka symbol for a digit", () => {
  const result = parseCourierLabel("[=] [=] Invoice 3\n[=] = Weight 1.5KG\nCash on Delivery 5 2,394");
  assert.equal(result.invoice, "3");
  assert.equal(result.cod_amount, "2394");
  assert.equal(result.weight_kg, "1.5");
});

test("reads invoice and COD values that OCR puts on the next line", () => {
  const result = parseCourierLabel(`
    Address Sample Road
    Area Dhaka
    Invoice No.:
    WEB-০০৮/২৬
    Cash on Delivery Total Amount:
    BDT ১,২৫,৪৯৯.৫০
    Printed: 14/11/26
  `);
  assert.equal(result.invoice, "WEB-008/26");
  assert.equal(result.cod_amount, "125499.50");
});

test("reads invoice and COD from a line shared with other fields", () => {
  const result = parseCourierLabel("Invoice #0008  SF-ID 120000001\nC.O.D. Amount: Tk. 0  Printed: 14/11/26");
  assert.equal(result.invoice, "0008");
  assert.equal(result.tracking_id, "120000001");
  assert.equal(result.cod_amount, "0");
});

test("does not use the adjacent tracking ID, printed date, or COD fee as field values", () => {
  const result = parseCourierLabel("Invoice Number\nSF-ID 120000001\nCOD Fee: 120\nCash on Delivery\n14/11/26");
  assert.equal(result.invoice, "");
  assert.equal(result.cod_amount, "");
});

test("suggests a delivery zone and leaves unclear addresses for review", () => {
  assert.equal(suggestDeliveryZone("Dhaka Road", "Ambarkhana, Sylhet"), "outside");
  assert.equal(suggestDeliveryZone("House 12, Dhanmondi", ""), "inside");
  assert.equal(suggestDeliveryZone("সাভার, ঢাকা", ""), "outside");
  assert.equal(suggestDeliveryZone("বাসা ১২, মিরপুর", ""), "inside");
  assert.equal(suggestDeliveryZone("House 12, Road 4", ""), "");
});
