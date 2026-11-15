# Ecommerce administration

Open **ECOMMERCE ADMIN** from the existing admin sidebar, or visit `/ecommerce/dashboard`. The showroom/wholesale workspace remains at `/admin`. Existing product, inventory, employee and wholesale routes remain available to their original users.

## Navigation

| Section | Route | Workflow |
| --- | --- | --- |
| Dashboard | `/ecommerce/dashboard` | Delivered revenue, fulfilment queue, recent orders, support and stock alerts |
| Products | `/ecommerce/products` | Add/import a main product, set independent prices/discounts, assign brand/vendor and publish |
| Categories & Brands | `/ecommerce/categories` | Online categories and brand records; main categories remain separate |
| Inventory | `/ecommerce/inventory` | Online counts, reasoned adjustments, update/delete history |
| Orders | `/ecommerce/orders` | Verify advance delivery payment, confirm, ship, deliver or cancel |
| Customers | `/ecommerce/customers` | Customer directory and order history; account deletion is owner-admin only |
| Payments | `/ecommerce/payments` | Manual payment, COD and refund records; verified records are locked |
| Shipping & Delivery | `/ecommerce/shipping` | District-specific checkout fees, courier names and estimated delivery windows |
| Returns & Refunds | `/ecommerce/returns` | Request, approve, inspect and receive an online return; optionally restock |
| Marketing & Promotions | `/ecommerce/campaigns` | Scheduled website announcements, campaign plans and checkout coupons |
| Website Content | `/ecommerce/content` | Draft/publish pages, banners and FAQs |
| Reviews & Ratings | `/ecommerce/reviews` | Moderate and publish reviews; customer submissions require a delivered purchase |
| Customer Support | `/ecommerce/support` | Track enquiry status and write replies visible in the customer's support account |
| Suppliers & Purchases | `/ecommerce/purchases` | Supplier directory and draft-to-received purchasing |
| Finance & Accounting | `/ecommerce/finance` | Separate manual income/expense ledger with references |
| Reports & Analytics | `/ecommerce/reports` | Order status totals, latest 30 delivered-sales dates and CSV export |
| SEO Management | `/ecommerce/seo` | Public-page title, description, canonical, social image and robots metadata |
| Employees & Roles | `/ecommerce/team` | Dedicated ecommerce accounts with server-enforced module permissions |
| Multi-vendor Management | `/ecommerce/vendors` | Approve/suspend vendors, record commission agreements and assign their products |
| Language & Currency | `/ecommerce/locales` | Active languages, default selection, symbols and manually maintained display rates |
| Settings | `/ecommerce/settings` | Store identity, contact information, policies, low-stock threshold, delivery/payment settings |
| Security & Activity Logs | `/ecommerce/audit` | Read-only ecommerce mutations and denied actions, including login attempts |

## Data isolation and migrations

New ecommerce models live in separate `ecommerce_*` tables. Existing main products remain `sales_channel=main`; no stock is automatically transferred or copied. Online purchasing and accepted returns write only the stock row belonging to the online product and create an online stock adjustment.

`products.0008` adds optional brand/vendor references and category channels. `products.0009` copies category names for existing online products and changes only those online products' category references. It does not rename main categories or modify showroom, wholesale, main stock or previous financial records. Existing account roles remain unchanged; `accounts.0003` adds the new `ecommerce_staff` choice.

Apply migrations with the normal `python manage.py migrate --noinput`. Render's existing `python start.py` applies them before starting the API. Deploy backend before frontend. Existing order price snapshots and cancellation stock destinations are preserved.

## Daily workflows

1. Add online categories/brands and, if applicable, approve a vendor.
2. Create an online product or import a main product. Enter online prices, offers and allocated initial quantity, then publish.
3. For replenishment, add a supplier and create a draft purchase. Change it to **received** only when stock arrives. This adds stock once; received/cancelled purchases are locked. Supplier invoices are stock receipts, not automatic expense/payment entries.
4. Configure district names as comma-separated values in Shipping. Matching is case-insensitive and exact after trimming; the earliest active matching zone is used. Other cities use the existing default shipping fee. Checkout recalculates and validates the selected city's fee before accepting an order.
5. Verify delivery charge payment, confirm, ship and deliver through Orders. Record verified COD collection after delivery. Record expenses and other income in the separate Finance ledger.
6. Customers use `/support` to ask questions, review delivered products or request returns. Inspect returns, approve them, then receive them once. Accepted restocking adds online stock once. Refund requests cannot exceed the item's proportion of the paid order value after coupon discounts. Actual refunds are arranged with the customer and recorded in Payments with a reference.

Payment records do not execute a bank transfer. Verified totals are checked against the order's delivery/product balance. Verified refunds cannot exceed previously recorded verified collections. Recording verified delivery payments totalling the delivery fee also marks that order's delivery payment verified. Cancellation is not an automatic refund.

Completed stock/payment documents and team history cannot be deleted through these APIs. Use a reasoned stock adjustment, a separate correction/refund record or deactivate staff access. Every successful/denied mutation is logged without request bodies, passwords or tokens.

## Roles

Only the owner admin can manage ecommerce logins or read the security log. New team accounts use `ecommerce_staff`; they cannot access the existing main-stock, showroom, wholesale or general employee APIs.

| Role | Write access |
| --- | --- |
| Manager | Store operations, content, vendors, settings and finance; no team/security administration |
| Catalog manager | Online products, brands, inventory, content, SEO and reviews |
| Fulfilment | Orders, online inventory, shipping and returns |
| Customer support | Tickets, reviews and returns; read-only order/customer access |
| Finance | Payment records, online ledger, purchases and suppliers; read-only orders |
| Viewer | Read-only dashboard, catalog, inventory, orders and reports |

Deactivating a membership immediately prevents ecommerce API access, including with an existing JWT. Account passwords use the existing Django validators and hashes. Existing showroom/admin logins and roles are not reassigned.

## Public website integration

Published pages are available at `/pages/<slug>`. Published banners and approved reviews appear on the storefront. Active website campaigns appear only between their start/end times. Saved return/privacy policies are linked automatically. Storefront brands can be filtered. Suspended vendors' products cannot be publicly purchased.

English/Bangla support labels and display currency selections are available in the store preference bar. Product/page copy is authored by the administrator; adding a locale does not automatically translate that content. Conversion rates are manually maintained units of display currency per BDT. BDT must remain at rate 1; checkout, payment verification and accounting settle in BDT.

SEO metadata is applied in the rendered browser application. This Vite SPA does not gain server-rendered metadata or guaranteed social-crawler previews from these records; that requires a separate prerender/SSR integration. Content is rendered as text, not untrusted HTML.

## External integrations

This release supplies working admin records and customer workflows. It does not claim payment gateway execution, automatic refunds, courier-label booking, email/SMS campaign dispatch, automatic exchange-rate feeds, vendor self-service portals or vendor payouts. Those services require separate provider integrations and credentials. Vendor commission percentages are agreement records; they do not automatically produce settlements. Finance ledger balance is recorded income minus recorded expense, not a complete double-entry accounting or automatic profit statement.

## Validation

Backend tests cover permission boundaries, main-data isolation, category migration, purchase receipt idempotency, return limits and restocking, payment verification/limits, district shipping, publication, reviews, support ownership, locale validation and role restrictions. Browser QA uses an isolated demo database and verifies all module pages, desktop/mobile layout, main-product import and purchase receiving. Demo accounts/databases are not included in the repository or applied to the business database.
