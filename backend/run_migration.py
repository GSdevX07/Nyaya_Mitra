"""
Run the Supabase migration to create the uploaded_documents table.
Uses the Supabase Management API (not PostgREST) to execute raw SQL.
"""
import os, requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# Extract project ref from URL: https://<ref>.supabase.co
project_ref = SUPABASE_URL.replace("https://", "").split(".supabase.co")[0]
print(f"Project ref: {project_ref}")

sql = open("create_uploaded_documents_table.sql").read()

# Option 1: Supabase Management API v1
mgmt_url = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
resp = requests.post(
    mgmt_url,
    headers={
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    },
    json={"query": sql},
    timeout=30,
)
print("Mgmt API status:", resp.status_code)
print("Mgmt API body:", resp.text[:1000])

if resp.status_code not in (200, 201):
    # Option 2: Try using psycopg2 directly with the Supabase Postgres connection
    print("\nTrying direct psycopg2 connection...")
    db_password = os.environ.get("DB_PASSWORD", "")
    db_host = f"db.{project_ref}.supabase.co"
    db_conn_str = f"postgresql://postgres:{db_password}@{db_host}:5432/postgres"
    try:
        import psycopg2
        conn = psycopg2.connect(db_conn_str, connect_timeout=15, sslmode="require")
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        conn.close()
        print("✓ Migration executed via psycopg2 successfully!")
    except Exception as e:
        print(f"psycopg2 failed: {e}")
        print("\n⚠  Please run create_uploaded_documents_table.sql manually in the Supabase SQL editor.")
else:
    print("✓ Migration executed via Management API successfully!")
