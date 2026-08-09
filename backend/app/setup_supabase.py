"""
setup_supabase.py — Initialize Supabase PostgreSQL tables and seed data.
"""

import os
import json
import hashlib
import datetime
import psycopg2
from dotenv import load_dotenv

# Load env
load_dotenv()
DB_PASSWORD = os.environ.get("DB_PASSWORD")

# Hardcoded for now based on earlier diagnostics
HOST = "aws-0-ap-south-1.pooler.supabase.com"
PORT = 5432
USER = "postgres.bqvgxarromdjjrzflrwy"
DBNAME = "postgres"

DDL = """
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS evidence;
DROP TABLE IF EXISTS cases;

CREATE TABLE cases (

    case_id TEXT PRIMARY KEY,
    data JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    stored_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    is_read INTEGER DEFAULT 0
);
"""

def setup_db():
    print("Connecting to Supabase PostgreSQL...")
    conn = psycopg2.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=DB_PASSWORD,
        dbname=DBNAME
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("Creating tables...")
    cursor.execute(DDL)
    print("Tables created successfully.")
    
    # Check if empty
    cursor.execute("SELECT COUNT(*) FROM cases;")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("Database is empty. Seeding data...")
        from app.main import MOCK_DB
        
        for case in MOCK_DB:
            cursor.execute(
                "INSERT INTO cases (case_id, data) VALUES (%s, %s)",
                (case.case_id, case.model_dump_json())
            )
            
            for doc in case.present_docs:
                evidence_id = f"EVI-{case.case_id}-{doc}"
                file_name = f"{doc}.pdf"
                mock_file_bytes = f"mock_file_content_for_{case.case_id}_{doc}".encode()
                stored_hash = hashlib.sha256(mock_file_bytes).hexdigest()
                
                if case.case_id == "UTP-0012" and doc == "remand_order":
                    stored_hash = "deadbeef" + stored_hash[8:]
                    
                cursor.execute(
                    "INSERT INTO evidence (evidence_id, case_id, document_type, file_name, stored_hash, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (evidence_id, case.case_id, doc, file_name, stored_hash, datetime.datetime.now(datetime.timezone.utc).isoformat())
                )
                
            if case.case_id == "UTP-0007":
                cursor.execute(
                    "INSERT INTO notifications (id, case_id, title, message, type, timestamp, is_read) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (f"NOTIF-{case.case_id}-mock", case.case_id, "High Priority Bail Eligibility Flagged", f"{case.case_id} has exceeded the sentence threshold.", "urgent", datetime.datetime.now(datetime.timezone.utc).isoformat(), 0)
                )
        print("Seeding complete.")
    else:
        print(f"Database already contains {count} cases. Skipping seed.")
        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    setup_db()
