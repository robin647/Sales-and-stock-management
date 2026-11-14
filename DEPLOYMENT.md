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

Product image uploads are saved under `backend/media/products/`. The relative image path is stored in PostgreSQL. Local uploaded files are intentionally ignored by Git; the Compose backend mounts this directory so container restarts do not discard files.

## Neon Production Database

1. In Neon, open the production branch and copy the PostgreSQL connection string used by the live Render service. Neon offers direct and pooled URLs; use the existing working production `DATABASE_URL` so migrations and the API use the same configured database.
2. In Render, open the `sales-and-stock-management` service environment and confirm its existing `DATABASE_URL` points to the Neon production database. No additional migration URL variable is required.
3. Set `ALLOWED_HOSTS` to the Render API hostname and `CORS_ALLOWED_ORIGINS` to the deployed frontend origin. In Vercel's project environment, set `VITE_API_URL` to `https://<render-api-host>/api` and redeploy the frontend.
4. Keep `LOCAL_DATABASE_URL` local only. Render's production settings use `DATABASE_URL`; no Neon credentials belong in GitHub or `.env.example`.
5. Set the Render service's **Start Command** to `python start.py` (with root directory `backend`). Existing manually configured services may retain their old command even after `render.yaml` changes. The startup script applies migrations and checks for pending schema changes before starting Gunicorn. Check deploy logs to confirm the accounts and products migrations completed.

### Product catalog returns HTTP 500

If `/api/products/categories/` works but `/api/products/?is_active=true&page_size=100&page=1` returns 500, inspect the Render traceback. A missing `products_product.image` or `discount_price` column means the deployed code and database schema are out of sync.

In the Render Shell (from the backend directory), run:

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

`render.yaml` mounts a persistent disk at `/var/data` and sets `MEDIA_ROOT=/var/data/media`. Django stores uploaded binaries there and stores only their relative paths in Neon. The `/media/` endpoint serves those files through the API. The disk survives application deploys; keep its mount path and `MEDIA_ROOT` aligned. Files in a developer's ignored local `backend/media/` directory are not included in Git and must be uploaded to the deployed app separately.

## Deploy From GitHub

1. Commit and push the migrations, backend, frontend, and `render.yaml` changes to the GitHub branch connected to Render and Vercel.
2. Render builds the API and deploys after the migration command succeeds. Vercel builds the frontend after push.
3. Check Render deploy logs for successful migrations and Vercel deployment status, then open the deployed frontend URL.

Never commit `.env.local`, `backend/.env`, Neon connection strings, uploaded customer/product files, or secret keys.
