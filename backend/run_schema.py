"""
run_schema.py
─────────────
Executes the Supabase SQL schema via the REST management API.
Run this BEFORE seed_supabase.py to create all tables.
"""
import os, requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# Read the schema SQL file
schema_path = os.path.join(os.path.dirname(__file__), "supabase_schema.sql")
with open(schema_path, "r", encoding="utf-8") as f:
    sql = f.read()

# Execute via Supabase REST SQL endpoint
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

resp = requests.post(
    f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
    headers=headers,
    json={"sql": sql},
    timeout=30,
)

if resp.status_code in (200, 201, 204):
    print("✅ Schema applied successfully via RPC!")
else:
    # Fallback: run statements individually through postgrest
    print(f"RPC exec_sql not available (status {resp.status_code}) applying schema statement by statement...")
    
    # Split SQL into individual statements  
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
    
    passed = 0
    failed = 0
    for stmt in statements:
        if not stmt.strip():
            continue
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"query": stmt + ";"},
            timeout=15,
        )
        if r.status_code in (200, 201, 204):
            passed += 1
        else:
            print(f"  ⚠ Failed ({r.status_code}): {stmt[:80]}...")
            print(f"    Response: {r.text[:200]}")
            failed += 1
    
    print(f"\n{passed} statements passed, {failed} failed.")
    if failed == 0:
        print("✅ Schema applied successfully!")
