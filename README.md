# Mahir Sherwani — Showroom Stock & Sales Management System

A centralized system for managing daily stock and sales/balance across 5 showrooms:
Mahadi Zone-1, Mahadi Zone-2, Mahadi Zone-3, Mahadi Zone-4, and Mahir Sherwani.

- **Admin** manages showrooms, products, and views reports across all showrooms.
- **Showroom User** logs in and can only see/update their own showroom's daily stock and balance.

## Customer email signup and separate portals

| Workspace | URL |
| --- | --- |
| Public ecommerce | `/` |
| Customer signup / login | `/signup` / `/login` |
| Existing customer email verification | `/verify-email` |
| Administration login / dashboard | `/admin/login` / `/admin/dashboard` |
| Ecommerce administration | `/admin/ecommerce/dashboard` |
| Showroom login / dashboard | `/showroom/login` / `/showroom/dashboard` |

Admin features now use `/admin/...`; showroom features use `/showroom/...`.
Old feature links redirect to their new addresses. API URLs remain under `/api/`.
Staff continue using their existing usernames and passwords. Customers use a
verified email and their own password. Signup emails contain a six-digit OTP,
valid for **60 seconds after the mail service accepts it**, usable once. Resend
requires a 60-second wait; five wrong attempts invalidate that code.

Existing customers, orders, showroom data, wholesale data and main stock are
preserved. Existing customers verify the email already saved on their account at
`/verify-email`, then log in using that email and their existing password. Accounts
sharing an email are not automatically merged; an administrator must first give
each account its correct unique email. Existing access tokens expire normally;
unverified customers cannot refresh them or log in again before verification.

### Gmail setup: mhrobin471@gmail.com

**আপনাকে Google account-এর অনুমতি দিতে হবে।** কোডে Gmail HTTPS API সংযোগ তৈরি
করা আছে, কিন্তু আপনার Google credentials ছাড়া আসল OTP পাঠানো চালু হবে না।
Credentials chat, GitHub বা frontend environment-এ দেবেন না; শুধু backend-এর
private environment settings-এ রাখবেন। Customers-কে Google login করতে হবে না।

Render Free [blocks SMTP ports 25, 465 and 587](https://render.com/docs/free).
Production therefore uses the Gmail API over HTTPS, rather than Gmail SMTP.

1. Sign in as **mhrobin471@gmail.com** at [Google Cloud Console](https://console.cloud.google.com/).
   Create/select a project, then enable **Gmail API** in APIs & Services → Library.
2. In Google Auth Platform, configure Branding, Audience and Data Access. Use an
   External audience for a personal Gmail account, enter your app/support details,
   and request only `https://www.googleapis.com/auth/gmail.send`. During Testing,
   add **mhrobin471@gmail.com** as a test user. Only the sender authorizes this
   Google application; customers just receive email.
3. Create an OAuth client of type **Web application**. Add the exact authorized
   redirect URI `https://developers.google.com/oauthplayground`. Save its client
   ID and client secret privately.
4. Open [OAuth Playground](https://developers.google.com/oauthplayground/).
   In its settings, enable **Use your own OAuth credentials**, enter that client
   ID/secret, and use offline access with a consent prompt. In Step 1 enter
   `https://www.googleapis.com/auth/gmail.send`, authorize as **mhrobin471@gmail.com**,
   then in Step 2 exchange the authorization code for tokens. Save the **refresh
   token**, not the short-lived access token. Never share the token or screenshots
   containing it. You can remove the Playground redirect URI after obtaining it.
5. For sustained operation, move the consent app to **In production** and complete
   any verification Google requests. External apps in Testing normally receive
   refresh tokens that expire after **seven days** for Gmail scopes. After changing
   publishing status, repeat authorization and replace the refresh token. Personal
   use may qualify for Google's verification exceptions; this does not guarantee
   approval for a wider public OAuth application.
6. In Render → backend service → Environment, add the following values and deploy
   again. For local development, put the same variables in `backend/.env`.

```dotenv
EMAIL_BACKEND=apps.accounts.email_backend.GmailApiEmailBackend
DEFAULT_FROM_EMAIL="Mahir Sherwani <mhrobin471@gmail.com>"
GMAIL_CLIENT_ID=your-private-google-client-id
GMAIL_CLIENT_SECRET=your-private-google-client-secret
GMAIL_REFRESH_TOKEN=your-private-google-refresh-token
OTP_DAILY_EMAIL_LIMIT=400
EMAIL_TIMEOUT=15
```

`render.yaml` declares these settings, but cannot create Google credentials or
update an existing service's private settings by itself. The sender must match
the Gmail account that authorized the refresh token. No frontend mail settings
are needed. Keep the existing database/JWT/CORS environment settings in place.

7. Apply migrations, check configuration and explicitly send yourself a test:

```bash
cd backend
python manage.py migrate
python manage.py check_email_setup
python manage.py check_email_setup --send-test-to mhrobin471@gmail.com
```

The first check verifies required settings are present; only the last command
tests Google credentials and sends a real email. If Render Free has no shell,
run the check locally with the same private backend settings; deployment runs
the migrations through the existing startup command. Finally, test `/signup`
with an email you control, check Inbox/Spam, and use the code within one minute.
An expired code needs a resend. Missing credentials or delivery failure produces
a safe error and never creates an unverified customer account.

Standard Gmail API usage is currently available without additional API charges
below Google's billing threshold; Gmail mailbox sending limits also apply.
Personal Gmail can block sending above approximately 500 messages/recipients per
day. This app reserves at most 400 OTP sends per calendar day across the backend
and five sends per email per hour, including failed delivery reservations; other
mail sent from the same mailbox still counts toward Google's limits. This is
suited to a small store, not unlimited free bulk email. Google's limits/pricing
can change. Reauthorize and replace the refresh token if consent is revoked or
Google expires it. Automated tests use a fake mailbox/mock transport and do not
prove delivery from your real Gmail account.

Optional **local-only SMTP alternative**: enable Google 2-Step Verification,
create a Gmail App Password (when offered), and set
`EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`,
`EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=True`,
`EMAIL_HOST_USER=mhrobin471@gmail.com`, and `EMAIL_HOST_PASSWORD` to that private
App Password. Never use your normal Gmail password. Render Free cannot use this
SMTP alternative.

Official setup references: [Gmail sending](https://developers.google.com/workspace/gmail/api/guides/sending),
[OAuth refresh tokens and testing expiry](https://developers.google.com/identity/protocols/oauth2/),
[verification exceptions](https://support.google.com/cloud/answer/13464323?hl=en),
[Gmail sending limits](https://support.google.com/mail/answer/22839?hl=en),
[API quotas and billing thresholds](https://developers.google.com/workspace/gmail/api/reference/quota),
[App Passwords](https://support.google.com/mail/answer/185833?hl=en).

## Tech stack

Security fixes, test commands, request limits, proxy/Redis setup and hosting DDoS
protection boundaries are documented in [SECURITY_REVIEW.md](SECURITY_REVIEW.md).

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

The admin business assistant works without an external AI API key. Its local
Bangla/Banglish language layer resolves employees, parties, stock, lots and dates,
then formats read-only database results. Admin access is required. It supports
follow-up questions and asks for a selection when names are ambiguous.
See [BUSINESS_ASSISTANT.md](BUSINESS_ASSISTANT.md) for examples and boundaries.

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
