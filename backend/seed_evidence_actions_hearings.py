"""
seed_evidence_actions_hearings.py
Seeds evidence_items, automated_actions, and hearings tables
based on ASSIGNED undertrial_cases in Supabase.
"""
import os
import uuid
from datetime import date, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env')
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Fetch all assigned cases
cases_res = sb.table('undertrial_cases').select(
    'id, name, offense_sections, jail_location, custody_days, max_sentence_days_for_offense, present_docs, age, health_flag, arrest_date'
).eq('assignment_status', 'ASSIGNED').execute()

cases = cases_res.data
print(f"Found {len(cases)} assigned cases to seed from.")

_counter = [0]
def uid(prefix='X'):
    _counter[0] += 1
    return f"{prefix}-{_counter[0]:04d}"

# ─── CLEAR OLD SEEDED DATA ─────────────────────────────────────────────────────
print("Clearing old data...")
sb.table('evidence_items').delete().neq('id', 'NONEXISTENT').execute()
sb.table('automated_actions').delete().neq('id', 'NONEXISTENT').execute()
sb.table('hearings').delete().neq('id', 'NONEXISTENT').execute()

# ─── SEED EVIDENCE ─────────────────────────────────────────────────────────────
evidence_rows = []
for c in cases:
    offense = ', '.join(c['offense_sections'])
    is_missing_docs = 'charge_sheet' not in (c['present_docs'] or [])
    
    # Remand Order Evidence
    evidence_rows.append({
        'id': uid('EV'),
        'case_id': c['id'],
        'title': f"Remand Order Record {c['name']}",
        'offense': offense,
        'verification_status': 'Verified Authentic',
        'authenticity_score': 97.2,
        'chain_of_custody': f"{c['jail_location']} → Magistrate Court → DLSA File",
        'flagged': False,
        'notes': f"Remand order authenticated via cryptographic hash. Custody: {c['custody_days']} days.",
    })
    
    # FIR / Arrest Log Evidence
    evidence_rows.append({
        'id': uid('EV'),
        'case_id': c['id'],
        'title': f"FIR & Arrest Log {c['name']}",
        'offense': offense,
        'verification_status': 'Pending Review' if is_missing_docs else 'Verified Authentic',
        'authenticity_score': 74.5 if is_missing_docs else 92.1,
        'chain_of_custody': f"Police Station → {c['jail_location']}",
        'flagged': is_missing_docs,
        'notes': 'Charge sheet missing manual verification required.' if is_missing_docs else 'All documents present. Chain-of-custody intact.',
    })

print(f"Inserting {len(evidence_rows)} evidence rows...")
sb.table('evidence_items').insert(evidence_rows).execute()

# ─── SEED AUTOMATED ACTIONS ────────────────────────────────────────────────────
action_rows = []
today = date.today()

for c in cases:
    threshold = c['max_sentence_days_for_offense'] // 2
    is_eligible = c['custody_days'] >= threshold
    is_missing_docs = len([d for d in ['remand_order', 'charge_sheet', 'prior_bail_order_if_any'] if d not in (c['present_docs'] or [])]) > 0
    is_medical = c['health_flag'] or c['age'] >= 60
    offense = ', '.join(c['offense_sections'])
    
    # BNSS 479 Bail Petition if eligible
    if is_eligible:
        action_rows.append({
            'id': uid('ACT'),
            'case_id': c['id'],
            'action_type': 'Draft BNSS 479 Bail Petition',
            'priority': 'HIGH',
            'status': 'Pending Execution',
            'description': f"Auto-draft bail petition for {c['name']} under Section 479 BNSS. "
                           f"Custody: {c['custody_days']} days vs threshold: {threshold} days. Offense: {offense}.",
            'created_at': today.isoformat(),
        })
    
    # Missing docs notice
    if is_missing_docs:
        missing = [d for d in ['remand_order', 'charge_sheet', 'prior_bail_order_if_any'] if d not in (c['present_docs'] or [])]
        action_rows.append({
            'id': uid('ACT'),
            'case_id': c['id'],
            'action_type': 'Send Missing Document Notice to DLSA',
            'priority': 'MEDIUM',
            'status': 'Pending Execution',
            'description': f"Request missing docs for {c['name']}: {', '.join(missing).replace('_', ' ').title()}. "
                           f"Facility: {c['jail_location']}.",
            'created_at': today.isoformat(),
        })
    
    # Medical bail reminder
    if is_medical:
        action_rows.append({
            'id': uid('ACT'),
            'case_id': c['id'],
            'action_type': 'File Medical/Humanitarian Bail Application',
            'priority': 'HIGH',
            'status': 'Pending Execution',
            'description': f"{c['name']} flagged for medical priority (Age: {c['age']}, Health Flag: {c['health_flag']}). "
                           f"Urgent humanitarian bail application required under CrPC 437.",
            'created_at': today.isoformat(),
        })
    
    # Standard court appearance reminder
    action_rows.append({
        'id': uid('ACT'),
        'case_id': c['id'],
        'action_type': 'Schedule Next Remand Review',
        'priority': 'LOW',
        'status': 'Scheduled',
        'description': f"Routine remand review for {c['name']} at {c['jail_location']}. "
                       f"Offense: {offense}. Custody duration: {c['custody_days']} days.",
        'created_at': today.isoformat(),
    })

print(f"Inserting {len(action_rows)} action rows...")
sb.table('automated_actions').insert(action_rows).execute()

# ─── SEED HEARINGS ─────────────────────────────────────────────────────────────
hearing_rows = []
courts = {
    'Central Jail, Tihar (Synthetic)': 'Tis Hazari Courts, New Delhi (Synthetic)',
    'District Jail, Patna (Synthetic)': 'Patna Civil Court, Bihar (Synthetic)',
    'Sub-Jail, Jaipur (Synthetic)': 'Jaipur District Court, Rajasthan (Synthetic)',
    'Central Prison, Nagpur (Synthetic)': 'Nagpur District Sessions Court (Synthetic)',
}
judges = [
    'Hon. Justice A.K. Mehta (Synthetic)',
    'Hon. Justice P.R. Verma (Synthetic)',
    'Hon. Justice S. Chauhan (Synthetic)',
]

for i, c in enumerate(cases):
    court = courts.get(c['jail_location'], f"{c['jail_location']} Magistrate Court (Synthetic)")
    judge = judges[i % len(judges)]
    threshold = c['max_sentence_days_for_offense'] // 2
    is_eligible = c['custody_days'] >= threshold
    offense = ', '.join(c['offense_sections'])
    
    # Upcoming bail hearing
    hearing_date_1 = (today + timedelta(days=7 + i * 3)).isoformat()
    hearing_rows.append({
        'id': uid('HRG'),
        'case_id': c['id'],
        'prisoner_name': c['name'],
        'court_name': court,
        'hearing_date': hearing_date_1,
        'hearing_type': 'Bail Application Hearing (Section 479 BNSS)' if is_eligible else 'Bail Application Hearing (Humanitarian)',
        'status': 'Scheduled',
        'judge': judge,
    })
    
    # Remand review
    hearing_date_2 = (today + timedelta(days=14 + i * 5)).isoformat()
    hearing_rows.append({
        'id': uid('HRG'),
        'case_id': c['id'],
        'prisoner_name': c['name'],
        'court_name': court,
        'hearing_date': hearing_date_2,
        'hearing_type': 'Judicial Remand Review',
        'status': 'Scheduled',
        'judge': judge,
    })

print(f"Inserting {len(hearing_rows)} hearing rows...")
sb.table('hearings').insert(hearing_rows).execute()

print("Done! All tables seeded successfully.")
