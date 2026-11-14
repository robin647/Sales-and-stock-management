import assert from "node:assert/strict";
import test from "node:test";
import { compareFeaturedProducts } from "./storefrontSort.js";

test("more orders come first, then new arrivals; manual feature flag does not override them", () => {
  const products = [
    { id: 1, popularity_orders: 0, created_at: "2026-01-01", is_featured: true },
    { id: 2, popularity_orders: 5, created_at: "2026-01-01" },
    { id: 3, popularity_orders: 5, created_at: "2026-02-01" },
    { id: 4, popularity_orders: 0, created_at: "2026-03-01" },
  ];
  assert.deepEqual(products.sort(compareFeaturedProducts).map(p => p.id), [3, 2, 4, 1]);
});

test("missing popularity falls back to newest; equal dates have a stable ID order", () => {
  const products = [{ id: 1, created_at: "2026-01-01" }, { id: 2, created_at: "2026-02-01" }, { id: 3, created_at: "2026-02-01" }];
  assert.deepEqual(products.sort(compareFeaturedProducts).map(p => p.id), [3, 2, 1]);
});
