# Mahir Sherwani — Showroom Stock & Sales Management System

A centralized system for managing daily stock and sales/balance across 5 showrooms:
Mahadi Zone-1, Mahadi Zone-2, Mahadi Zone-3, Mahadi Zone-4, and Mahir Sherwani.

- **Admin** manages showrooms, products, and views reports across all showrooms.
- **Showroom User** logs in and can only see/update their own showroom's daily stock and balance.

## Tech stack

- Backend: Django, Django REST Framework, PostgreSQL, JWT (SimpleJWT), Gunicorn, WhiteNoise
- Frontend: React (Vite), React Router, Axios, Tailwind CSS, Recharts
- Database: **PostgreSQL only** (local and production)

---

## 1. Local development (without Docker)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set DATABASE_URL to point at your local PostgreSQL instance

# Make sure PostgreSQL is running and the database/user in .env exist, e.g.:
#   createuser mahir_user --pwprompt
#   createdb mahir_showroom -O mahir_user

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`.

### Frontend

```bash
cd frontend
cp .env.example .env   # VITE_API_URL=http://localhost:8000/api
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## 2. Local development with Docker

```bash
docker compose up --build
```

This starts:
- `db` — PostgreSQL 16
- `backend` — Django + Gunicorn on port 8000 (migrations run automatically on startup)
- `frontend` — React build served by nginx on port 3000

Then create an admin user inside the running backend container:

```bash
docker compose exec backend python manage.py createsuperuser
```

Visit `http://localhost:3000`.

---

## 3. First-time setup after deployment (either method)

1. Log in to `/admin/` (Django admin) with the superuser you created, or use the API.
2. As Admin, create the 5 showrooms (Mahadi Zone-1 … Mahir Sherwani).
3. Create product categories (Panjabi, Pajama, Shirt, Shoe, …) and products.
4. From the app's **Showrooms** page, create a login (username/password) for each showroom — this automatically ties that user to their showroom with the `showroom_user` role.
5. Give the credentials to each showroom to start logging daily stock and balance.

---

## 4. Production deployment

The production stack is Neon (PostgreSQL), Render (Django API), and Vercel (React/Vite frontend). Follow [DEPLOYMENT.md](DEPLOYMENT.md) for the exact setup order, dashboard values, migration commands, and verification steps. The root `render.yaml` configures the Render API service; `frontend/vercel.json` configures Vercel client-side routing.

## 5. Project structure

```
backend/    Django REST API (see backend/apps/*)
frontend/   React SPA (see frontend/src)
docker-compose.yml   Local multi-service dev environment
```

Key business rules enforced server-side (not just in the UI):
- `Closing Stock = Opening + Received - Sold + Return`, cannot go negative.
- Yesterday's closing stock/balance automatically becomes today's opening — the frontend never sends `opening_qty` / `opening_balance`.
- `Total Sale = Cash Sale + Card Sale`; `Closing Balance = Opening + Cash - Expense - Salary - Deposit` (card sale is excluded from the cash closing balance).
- One stock entry per (showroom, product, date) and one balance entry per (showroom, date) — enforced by database unique constraints.
- A showroom user's `showroom_id` is always taken from their own JWT/account on the server, never trusted from the request body — so a tampered frontend request cannot write to another showroom.

## 6. Environment variable reference

See `backend/.env.example` and `frontend/.env.example` for the full list.
