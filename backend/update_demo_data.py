import os
import random
from dotenv import load_dotenv
from supabase import create_client

# Names dictionary
first_names = ["Ramesh", "Suresh", "Amit", "Rajesh", "Vijay", "Sunil", "Anil", "Sanjay", "Sita", "Sunita", "Gita", "Pooja", "Priya", "Anjali", "Ravi", "Manoj", "Deepak", "Vikram", "Rahul", "Neha", "Anita"]
last_names = ["Kumar", "Sharma", "Singh", "Patel", "Verma", "Yadav", "Gupta", "Das", "Devi", "Chauhan", "Bauri", "Mishra", "Jain", "Nair"]

offense_types = [
    {"code": "IPC_379", "sections": ["IPC 379", "BNSS 303"], "max_sentence": 1095},
    {"code": "IPC_323", "sections": ["IPC 323"], "max_sentence": 365},
    {"code": "NDPS_21", "sections": ["NDPS 21"], "max_sentence": 3650},
    {"code": "EXCISE_34", "sections": ["Excise Act 34"], "max_sentence": 1095},
    {"code": "IPC_420", "sections": ["IPC 420"], "max_sentence": 2555},
]

jails = ["Central Jail, Tihar (Synthetic)", "District Jail, Patna (Synthetic)", "Sub-Jail, Jaipur (Synthetic)", "Central Prison, Nagpur (Synthetic)"]

def generate_name():
    return f"{random.choice(first_names)} {random.choice(last_names)} (Synthetic)"

def update_cases():
    load_dotenv('.env')
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])
    
    res = sb.table("undertrial_cases").select("*").execute()
    cases = res.data
    
    print(f"Fetched {len(cases)} cases.")
    
    updates = []
    
    for i, c in enumerate(cases):
        name = generate_name()
        
        # 40% Eligible, 60% Ineligible
        is_eligible = random.random() < 0.4
        
        # Randomize offense
        offense = random.choice(offense_types)
        is_repeat = random.random() < 0.3
        
        threshold = offense["max_sentence"] // (3 if not is_repeat else 2)
        
        if is_eligible:
            custody_days = random.randint(threshold + 10, threshold + 300)
        else:
            custody_days = random.randint(10, max(11, threshold - 10))
            
        # 20% Medical Flag
        is_medical = random.random() < 0.2
        age = random.randint(61, 85) if random.random() < 0.15 else random.randint(18, 59)
        if age >= 60:
            is_medical = True
            
        # 30% Missing Docs
        has_missing_docs = random.random() < 0.3
        present_docs = ["remand_order", "charge_sheet", "prior_bail_order_if_any"]
        if has_missing_docs:
            present_docs.remove(random.choice(present_docs))
            
        # Merge with existing row data to avoid NOT NULL violations on upsert
        updated_case = c.copy()
        updated_case.update({
            "name": name,
            "offense_code": offense["code"],
            "offense_sections": offense["sections"],
            "max_sentence_days_for_offense": offense["max_sentence"],
            "custody_days": custody_days,
            "first_time_offender": not is_repeat,
            "health_flag": is_medical,
            "age": age,
            "present_docs": present_docs,
            "jail_location": random.choice(jails)
        })
        updates.append(updated_case)
        
    print("Updating in batches...")
    
    # Batch update
    for i in range(0, len(updates), 50):
        batch = updates[i:i+50]
        sb.table("undertrial_cases").upsert(batch).execute()
        print(f"Updated {i+len(batch)} / {len(updates)}")
        
    print("Done!")

if __name__ == "__main__":
    update_cases()
