# Security review and deployment notes

Reviewed 2026-11-17 (Asia/Dhaka). This is a source review and regression test
record, not a claim that every possible bug or attack has been eliminated.
No load/flood attacks were sent to the live site.

## Findings fixed

| Finding | Change |
| --- | --- |
| Showroom password change called a nonexistent method on stored refresh tokens | Create blacklist records inside the password-change transaction. Regression test confirms the new password and rejected old refresh token. Existing access tokens can remain valid until their normal expiry (15 minutes by default). |
| Admin login verified the same password twice | Authenticate once, apply the configured SimpleJWT active-user rule and portal role check, then issue tokens. Rejected portal roles do not create outstanding tokens. |
| A failed login could enter the generic refresh/retry flow for a previous session | Authentication failures stay on the login page and are never retried using a previous account's refresh token. Browser test covers this. |
| No early request guard for refresh endpoints, Django admin or oversized API bodies | Bounded per-IP counters run before authentication/database work; default 600 requests/minute and 20 authentication POSTs/minute, shared across authentication endpoints. Return 429 with Retry-After. Reject bodies over 5 MiB and query strings over 8 KiB before parsing. Health checks are exempt. |
| Forwarded headers could influence ordinary DRF throttle identities without explicit proxy configuration | Default to the socket peer; trust a configured position in X-Forwarded-For only with an explicit proxy count. The early guard validates and canonicalizes IP addresses. |
| Spreadsheet exports treated database strings beginning with `=` as formulas | All report, wholesale, salary, sewing and producer workbook exports convert formula cells to literal text before saving. Python-calculated numeric totals stay numeric. |
| Object permission helper could compare two missing showroom IDs as equal | Require showroom role and a non-null assigned showroom before matching an object. |
| Invalid ORM filter values could return a generic 500 | Django field validation and invalid value conversions now return a safe 400; request size exceptions return 413. User input is not echoed as SQL or traceback. |
| Team creation could leave an orphan login if membership creation failed | User and membership creation are atomic. |
| Frontend dependencies had published advisories | Update React Router, Vite and their dependencies. Node 22.12+ is required. Audit both production and development dependencies. |
| Static storage setting used the old Django API | Configure STORAGES for the deployed Django 5.2 version, including WhiteNoise manifest storage. |
| Frontend lacked browser security headers | Vercel headers enforce CSP, deny framing, disable unused sensitive browser capabilities and set content-type/referrer policies. CSP allows the current Render API, HTTPS product images and Google Fonts. |

Login/signup/password-change inputs also cap password length to avoid needlessly
hashing huge submitted values. Product uploads already decode and re-encode
images to WebP and check file size and pixel count; the request guard adds an
earlier transport size limit. Checkout already validates totals server-side,
locks stock, checks idempotency and scopes customer orders. Existing showroom,
wholesale, salary and main-stock data are not rewritten by these changes.

## SQL injection review

Reviewed Python query call sites for raw(), extra(), RawSQL, execute() and string
interpolation into SQL. Application request handlers use Django ORM filters and
aggregations; no request-derived raw SQL call was found. Keep using parameterized
ORM queries. Do not add a keyword blacklist: names, notes and Bangla text can
legitimately contain quotes or SQL-looking words. Tests include a SQL payload in
login and a malformed numeric query parameter without authentication bypass,
data deletion or a server error.

Reference: [Django SQL injection protection](https://docs.djangoproject.com/en/5.2/topics/security/#sql-injection-protection).

## Rate-limit and DDoS deployment

Application limits reduce abuse that reaches Django. They cannot absorb a
network-scale distributed flood. Both existing hosting providers include edge
protection: [Render](https://render.com/docs/ddos-protection) and
[Vercel](https://vercel.com/docs/vercel-firewall/ddos-mitigation). Their account
dashboards, traffic rules and incidents were not configured or inspected during
this source review. Do not treat passing unit tests as a DDoS capacity test.
[DRF also documents the limitations of application throttling](https://www.django-rest-framework.org/api-guide/throttling/).

Backend environment options:

```dotenv
REQUEST_GUARD_ENABLED=True
REQUESTS_PER_MINUTE=600
AUTH_REQUESTS_PER_MINUTE=20
TRUSTED_PROXY_COUNT=0
# Optional shared cache; use your private TLS Redis connection URL:
# SECURITY_REDIS_URL=rediss://username:password@host:port/0
```

* With no Redis URL, counters use a bounded in-memory cache shared by threads in
  one process. They reset on restart and are not shared across workers/instances.
  The current startup default is one Gunicorn worker. Before adding workers or
  instances, provision private Redis, set SECURITY_REDIS_URL on every instance
  and confirm cross-instance 429 behavior. This also shares DRF's throttle cache.
  Cache outages deliberately return a controlled 503 for guarded requests;
  health checks continue. Redis was not provisioned or integration-tested here.
* TRUSTED_PROXY_COUNT=0 ignores forwarded headers. Behind Render this may group
  clients under a proxy address and throttle unrelated visitors together. Inspect
  the actual trusted forwarding chain in your hosting configuration before
  changing it. Set 1 **only if the final forwarding proxy appends or overwrites
  the client IP in the rightmost X-Forwarded-For position**; use the correct count
  for other chains. Never trust arbitrary caller-supplied header positions or
  enable direct origin access around a configured trusted proxy. Verify two
  different client networks have separate limits and spoofed prefixes do not
  bypass the limit. No client-proxy chain was verified from production logs here.
* Use hosting firewall/bot/rate-limit rules for sustained abuse. Challenge or
  block abusive clients on login, OTP and expensive export/report endpoints;
  preserve health probes and CORS preflights. Monitor 429/503 rates before
  tightening thresholds. Users behind a shared NAT share per-IP budgets.
* The middleware rejects declared oversized requests; reverse-proxy request-body,
  header, connection and timeout limits are still needed for chunked/slow/flood
  traffic before it reaches the Python process. Never expose Vite development
  servers publicly. Existing Gunicorn timeout and worker bounds remain in place.

## Browser and secrets configuration

The production CSP in frontend/vercel.json allows API connections to
`https://sales-and-stock-management.onrender.com` and the same origin. If you
change VITE_API_URL to another API host, update connect-src at the same time.
The browser smoke test must build with that production API origin. HTTP localhost
development uses Vite without Vercel headers. No inline scripts or eval are
allowed; inline styles remain allowed for React layout, themes and print labels.

Keep SECRET_KEY, DATABASE_URL, Gmail refresh tokens and Redis credentials only
in backend private settings. Use a database account with access to the app's
database only, TLS where provided, and a tested backup/restore process. Avoid
logging request bodies or credentials. Rotate leaked keys and invalidate tokens.
The review does not inspect private account dashboards, historical secret leaks
or database backup configuration. Gmail owner authorization remains a separate
README setup step.

## Reproduce validation

`.github/workflows/security.yml` runs dependency audits, builds and PostgreSQL
regression tests for pushes/PRs, manual runs and a weekly schedule. It uses only
an isolated CI database and dummy CI credentials, never the production database.
Repository branch protection must be enabled separately if these checks are to
block merging; this review does not change GitHub account settings.

```bash
cd backend
python manage.py test config core.test_security apps.accounts.test_email_auth apps.accounts.test_customers apps.accounts.tests apps.assistant.tests apps.ecommerce.tests apps.products.tests apps.products.test_codes apps.products.test_online_inventory apps.shop.tests apps.wholesale.tests apps.reports.tests apps.employees.tests apps.producers.tests apps.swing.tests --noinput
python manage.py makemigrations --check --dry-run
python -m pip_audit -r requirements.txt --progress-spinner off

cd ../frontend
npm ci
npm audit
npm run build
# Set VITE_API_URL to the current production Render /api URL for this build.
# Chrome must be installed; set CHROME_PATH if its location differs.
npm run test:security-smoke
```

Browser checks use mocked API responses: public signup/login/verification screens,
admin/showroom login redirects, legacy links, CSP rendering and failed-login
refresh isolation. They do not prove real Gmail delivery or live backend health.
Concurrency-sensitive stock tests require PostgreSQL; SQLite skips those tests.
Audit results are a snapshot of the vulnerability databases at execution time.
On this review, both frontend audit and backend requirement/installed-environment
audits reported no known vulnerabilities. All 214 tests passed against a fresh,
isolated local PostgreSQL test database, including both checkout concurrency
tests. The database was then removed by Django's test runner. SQLite regression
checks and the Chrome smoke test also passed. Test runs ignore an inherited
SECURITY_REDIS_URL so their cache resets cannot clear a live Redis cache.
