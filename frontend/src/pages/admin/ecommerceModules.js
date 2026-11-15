export const ecommerceGroups = [
  { title: "Overview", items: [["dashboard", "Dashboard", "◈"]] },
  { title: "Store operations", items: [["products", "Products", "▣"], ["categories", "Categories & Brands", "▦"], ["inventory", "Inventory", "▤"], ["orders", "Orders", "▧"], ["customers", "Customers", "♧"], ["payments", "Payments", "↔"], ["shipping", "Shipping & Delivery", "↗"], ["returns", "Returns & Refunds", "↩"]] },
  { title: "Growth & experience", items: [["campaigns", "Marketing & Promotions", "✧"], ["content", "Website Content", "▱"], ["reviews", "Reviews & Ratings", "☆"], ["support", "Customer Support", "☏"], ["seo", "SEO Management", "⌕"]] },
  { title: "Business", items: [["purchases", "Suppliers & Purchases", "⇣"], ["finance", "Finance & Accounting", "৳"], ["reports", "Reports & Analytics", "▥"], ["vendors", "Multi-vendor Management", "◇"]] },
  { title: "Administration", items: [["team", "Employees & Roles", "♙"], ["locales", "Language & Currency", "◎"], ["settings", "Settings", "⚙"], ["audit", "Security & Activity Logs", "⊙"]] },
];
export const ecommerceTitles = Object.fromEntries(ecommerceGroups.flatMap(group => group.items.map(([id, title]) => [id, title])));
