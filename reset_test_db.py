from pathlib import Path
from urllib.parse import urlparse
from psycopg import connect

p = Path(r"c:/Users/Md. Robin Hossain/Desktop/mahir-sherwani-showroom/mahir-sherwani-showroom/backend/.env")
env = {}
for line in p.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()

url = env["DATABASE_URL"]
parsed = urlparse(url)
conn = connect(
    host=parsed.hostname,
    dbname="postgres",
    user=parsed.username,
    password=parsed.password,
    port=parsed.port or 5432,
    sslmode="require",
)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='test_neondb';")
    cur.execute("DROP DATABASE IF EXISTS test_neondb;")
print("dropped test_neondb")
