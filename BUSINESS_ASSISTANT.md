# Local business assistant

The existing admin **Business AI** button runs a deterministic language/query engine
in Django. No Groq/OpenAI/other AI API, key, model download or new package is needed.
The browser still needs a connection to your backend/database. This is a business
question assistant, not a newly trained general language model; it handles supported
topics and paraphrases, asks for clarification and cannot understand every possible
question. Results are freshly read from approved ORM queries, not generated SQL.

## Examples

- `Robin er salary koto?` / `রবিনের বেতন কত?`
- `রবিনের নভেম্বর ২০২৬ মাসে অনুপস্থিতি ও নিট বেতন কত?`
- After asking about a worker: `or koi din absent?` / `তার অগ্রিম কত?`
- `Bor Kone party last payement koto ar due koto?`
- `বর কনের শেষ পেমেন্ট কত, বাকি কত?`
- `Bor Kone party 2026-11-05 payment koto?`
- `33 number lot ta ke selai korse?` / `৩৩ নম্বর লট কে সেলাই করেছে?`
- `মূল স্টক মোট কত আছে?` / `MS-000123 product stock koto?`
- `আজ Mahadi Zone-1 showroom sale koto?`
- `সব পার্টির মোট বাকি কত?` / `সব কর্মীর মূল বেতন মোট কত?`
- `<name> producer paid due koto?` / `<name> swing operator er hisab`

Use your actual names/codes. Suggestions load from existing records. Bangla and
Latin names are compared using normalisation, phonetic matching and conservative
fuzzy matching. Ambiguous names produce signed selection buttons. Answers are in
Bangla, identify their interpreted period and include record-source references.
**নতুন আলোচনা** clears the conversation context.

## Data interpretation

Basic salary is the employee's current basic salary. Monthly attendance, net pay,
advance, loan and deductions use that month's salary sheet. Without a month, those
queries explicitly use the current month. Missing sheets are not replaced by older
months or fabricated zeros. Monthly absence counts cannot identify absence dates;
net salary is calculated entitlement, not evidence of payment.

Latest wholesale payment is selected by payment date, then creation time, across
invoice and Easy wholesale records. Due and credit remain separate, matching the
existing report. Their arithmetic net position is also shown; no credit is applied
or account modified. Date-filtered payment queries retain clearly labelled all-time
due. Period-wide summaries follow the existing wholesale report's period logic.

Main-stock answers exclude online inventory. Historical factory counts are not
inferred from mutable current-stock rows. Lot 33 does not match lot 333; multiple
matching records are listed with operator/date/inactive status, up to 10. Showroom
closing balance is the last recorded balance in the period, not a sum of balances.

Supported time expressions include Bengali digits, ISO dates, day-month-year dates,
named months, today/yesterday and current/previous month. A named month without a
year uses the current server-local year; the interpreted period is shown.

## Access, privacy and deployment

Only `admin` accounts can query or load suggestions. Customers, showroom users and
ecommerce staff cannot read payroll/main-business data through this endpoint.
Password/token/API-key/NID requests and write/delete instructions are rejected.
Questions are never executed as SQL or code. Tests check that answers cause no
database mutations or external network calls.

Context contains selected identities and periods, not raw payroll records. It is
signed, tied to the admin account and expires after 30 minutes. Chat is held only
in the current browser component's memory; no database chat log is created.

No schema/model migration is needed. Existing Groq variables are unused; the Render
blueprint no longer asks for them. `/api/assistant/chat/` remains the endpoint:
GET returns actual-data suggestions; POST accepts a question and optional signed
context. Add new vocabulary/date patterns in `language.py`, approved query/format
handlers in `engine.py` and regression tests when extending coverage.
