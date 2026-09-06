import sqlite3
import glob
import re

# 1. Get all tables and columns from SQLite
conn = sqlite3.connect('backend/nyaya_mitra.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
sqlite_tables = {}
for (t_name,) in cursor.fetchall():
    if t_name.startswith('sqlite_'):
        continue
    cursor.execute(f"PRAGMA table_info({t_name});")
    cols = {c[1]: c[2] for c in cursor.fetchall()}
    sqlite_tables[t_name] = cols

print(f"Total SQLite Tables in nyaya_mitra.db: {len(sqlite_tables)}")
for t, cols in sorted(sqlite_tables.items()):
    print(f"  {t} ({len(cols)} cols)")

# 2. Get all tables and columns from all Supabase SQL files
sql_files = glob.glob('backend/*.sql')
supabase_tables = {}
for sf in sql_files:
    with open(sf, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    matches = re.finditer(r'CREATE TABLE IF NOT EXISTS\s+([a-zA-Z0-9_]+)\s*\((.*?)\);', content, re.DOTALL | re.IGNORECASE)
    for m in matches:
        t_name = m.group(1).lower()
        if t_name not in supabase_tables:
            supabase_tables[t_name] = set()
        body = m.group(2)
        for line in body.split('\n'):
            line = line.strip()
            if not line or line.startswith('--') or line.startswith('/*') or line.upper().startswith(('PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK', 'CONSTRAINT')):
                continue
            col = line.split()[0].strip(',"\'')
            if col and not col.upper().startswith(('PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK', 'CONSTRAINT')):
                supabase_tables[t_name].add(col.lower())

print(f"\nTotal Supabase Tables defined across SQL files: {len(supabase_tables)}")
for t, cols in sorted(supabase_tables.items()):
    print(f"  {t} ({len(cols)} cols)")

# 3. Compare tables
missing_in_supabase = set(sqlite_tables.keys()) - set(supabase_tables.keys())
print(f"\n==========================================")
print(f"TABLES IN SQLITE BUT MISSING IN SUPABASE SQL ({len(missing_in_supabase)}):")
for t in sorted(missing_in_supabase):
    print(f"  - {t}")

# 4. Compare columns for existing tables
print(f"\n==========================================")
print("MISSING COLUMNS IN SUPABASE TABLES (Columns in SQLite that are missing in Supabase):")
for t in sorted(sqlite_tables.keys()):
    if t in supabase_tables:
        sqlite_cols = set(c.lower() for c in sqlite_tables[t].keys())
        supa_cols = set(c.lower() for c in supabase_tables[t])
        missing_cols = sqlite_cols - supa_cols
        if missing_cols:
            print(f"Table '{t}': Missing {len(missing_cols)} columns in Supabase: {sorted(missing_cols)}")
