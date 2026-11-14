# Local PostgreSQL, Neon, and Deployment

## Local Development

The repository's Docker Compose file runs PostgreSQL on host port `5432`. From the repository root, start the database:

```powershell
docker compose up -d db
```

The ignored root `.env.local` uses `LOCAL_DATABASE_URL` for Django commands run on Windows. The default credentials are only for the local Compose database. If you use a separately installed PostgreSQL server, change its host, port, database, username, and password in `.env.local`.

Run migrations and start the API from `backend`:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Run the frontend from `frontend`:

```powershell
npm install
npm run dev
```

New product image uploads are resized to at most 1000×1000, compressed as WebP (maximum 250 KB), and stored in PostgreSQL. Product lists include a versioned image URL rather than binary content. Existing file-based photos continue to use `/media/`; re-upload those photos through the product editor to move them into database storage. An external image URL can also be used.

## Neon Production Database

1. In Neon, open the production branch and copy the PostgreSQL connection string used by the live Render service. Neon offers direct and pooled URLs; use the existing working production `DATABASE_URL` so migrations and the API use the same configured database.
2. In Render, open the `sales-and-stock-management` service environment and confirm its existing `DATABASE_URL` points to the Neon production database. No additional migration URL variable is required.
3. Set `ALLOWED_HOSTS` to the Render API hostname and `CORS_ALLOWED_ORIGINS` to the deployed frontend origin. In Vercel's project environment, set `VITE_API_URL` to `https://<render-api-host>/api` and redeploy the frontend.
4. Keep `LOCAL_DATABASE_URL` local only. Render's production settings use `DATABASE_URL`; no Neon credentials belong in GitHub or `.env.example`.
5. For the existing Docker service, clear any **Docker Command** override to use Dockerfile CMD, or set it to `python start.py`. Existing manually configured services may retain their old command even after `render.yaml` changes. The startup script applies migrations and checks for pending schema changes before starting Gunicorn. Check deploy logs to confirm the accounts and products migrations completed.

### Product catalog returns HTTP 500

If `/api/products/categories/` works but `/api/products/?is_active=true&page_size=100&page=1` returns 500, inspect the Render traceback. A missing `products_product.image` or `discount_price` column means the deployed code and database schema are out of sync.

On a machine connected to the affected database, run (Free Render services have no Dashboard Shell; they use the automatic startup migration instead):

```sh
python manage.py showmigrations products
python manage.py migrate --noinput
python manage.py migrate --check
```

Confirm `products.0003_product_discount_price` and `products.0004_product_image` are applied, then retry the product URL. Use `python start.py` as the Start Command and redeploy to keep future releases synchronized. If migrations are already applied, use the actual request traceback to investigate; do not reset the database or fake migrations.

## Uploaded Media On Render

### Legacy inventory migration collision

If migration stops with `relation "inventory_factorystock" already exists`, an older database may record `inventory.0002_factorystock_showroomstock_stocktransfer` instead of the current inventory migration. Do not blindly fake the new migration: the old schema may be missing `inventory_stockadjustment`.

Deploy the repair command, then run against the affected database:

```sh
python manage.py repair_legacy_inventory
python manage.py migrate --noinput
python manage.py migrate --check
```

The repair requires the known legacy migration, validates existing table columns, types, keys and relationships, creates the missing adjustment table, ensures showroom/product uniqueness, and records the current migration in one transaction. Existing stock rows are retained. Unexpected schema differences stop the repair before it changes the database. Run the commands separately for local and Render databases; repairing a local database does not update Neon.

`render.yaml` uses `runtime: docker`, explicitly selects `plan: free`, and does not request a persistent disk. New uploaded product images live in Neon and do not depend on Render's temporary filesystem. Free hosting still has database/storage/bandwidth limits; each optimised image uses up to 250 KB of database storage. Existing file-based media on Free Render is temporary, so re-upload legacy photos through the editor. External image URLs depend on their host staying available.

## Deploy From GitHub

If startup reports `corsheaders.E014`, remove the trailing slash from Render's `CORS_ALLOWED_ORIGINS`: use `https://sales-and-stock-management-s7d7.vercel.app` with no path. Settings normalize surrounding whitespace and trailing slashes, but actual URL paths remain invalid. This system-check error prevents migrations and Gunicorn startup, so Render may subsequently report a port scan timeout.

For the existing **Docker** Render service, Dockerfile `CMD` starts `python start.py`. If Render Settings has a **Docker Command** override, set it to `python start.py` (or clear it to use the Dockerfile CMD). The Blueprint uses paths relative to the repository root: Dockerfile `./backend/Dockerfile`, context `./backend`. If the existing service already has Root Directory `backend`, retain that layout and use Dockerfile `./Dockerfile`, context `.`. Gunicorn defaults to one worker with four threads for the Free instance; `GUNICORN_WORKERS` can override this on a larger plan.

Startup now detects the specific old inventory migration and runs the validated legacy repair before applying all remaining migrations. Fresh databases and databases already repaired skip that repair. A validation or migration error still stops startup and is printed in the deploy logs.

If a new deployment fails while an earlier commit remains Live, inspect the failed deployment's final build/runtime logs. The Live commit's API errors do not establish why the new build failed. Check the deployed commit ID after pushing the startup fix and deploying the latest commit.

1. Commit and push the migrations, backend, frontend, and `render.yaml` changes to the GitHub branch connected to Render and Vercel.
2. Render builds the API and deploys after the migration command succeeds. Vercel builds the frontend after push.
3. Check Render deploy logs for successful migrations and Vercel deployment status, then open the deployed frontend URL.

Never commit `.env.local`, `backend/.env`, Neon connection strings, uploaded customer/product files, or secret keys.

## Commerce rollout (Vercel + Render + Neon Free)

### Customer directory

Admin sidebar **Customers** opens `/admin/customers`. The directory supports name/email/phone search, account status and order filters, pagination, account/contact information, delivered product spend and complete paginated order details. Password hashes and permission data are not returned.

Deploy the backend before the frontend so `shop.0003_alter_order_customer` is applied automatically by startup. The migration changes the order/customer relation to nullable `SET_NULL`: deleting a customer removes their account and revokes existing refresh tokens, while existing orders, recipient/contact/address snapshots, order items and payment references remain available in Online orders. Deleting an account does not cancel/refund orders or restore reserved stock. The confirmation dialog requires typing `DELETE` and shows any ongoing order count. Only customer accounts can be deleted through this endpoint; staff/admin accounts are excluded. A newly registered account with the same phone number does not inherit the deleted account's orders.

1. Deploy the backend first. The startup script applies `products.0005` and the `shop` migrations automatically; no manual Shell or paid disk is needed. Wait for the backend deployment to become Live before deploying the updated frontend.
2. Vercel remains a static React build with `VITE_API_URL=https://sales-and-stock-management.onrender.com/api`. Existing SPA rewrites cover `/shop`, `/checkout`, `/my-orders`, `/products`, and `/online-orders`.
3. Sign in as Admin. Use **Products & Categories → Categories** to create/rename categories, then **Add product** to set photos, description, size/code, sale price, discount price or percentage, initial factory stock, featured status and online visibility. Later stock changes remain in **Product Stock Adjustment**.
4. Open **Orders, Coupons & Delivery → Delivery & payment**. Set the advance delivery charge, payment method/number, customer instructions and WhatsApp number before accepting orders. The seeded delivery fee is ৳120, but checkout cannot accept paid-delivery orders until a payment number is configured. Change this amount to your actual charge.
5. Customers pay only the delivery fee in advance, submit its transaction ID, and pay the product amount on delivery. Admin must verify the transaction in their payment account before confirming the order. No payment gateway or automatic bank verification is claimed. Duplicate transaction IDs are rejected.
6. Online checkout reserves/deducts **factory** stock in a transaction. Cancelling pending/confirmed orders restores that stock once. Showroom stock, daily balances and wholesale invoices are not changed by online orders. Online delivered revenue appears in the separate order summary; it is not automatically added to existing showroom cash reports.
7. Pending and confirmed cancellations require manual handling of any advance-delivery refund. Record refund details in private admin notes. Coupons do not apply to delivery fees and their use counter is retained on cancellation. Courier tracking is entered manually; there is no courier API integration.
8. Uploaded photos and orders use the existing Neon database. No new paid service or subscription is configured. Free-plan cold starts and provider quotas still apply. Customer saved products are kept in that browser; order history is private to their account.

Render plan limitations: https://render.com/docs/free · Blueprint Docker configuration: https://render.com/docs/blueprint-spec
