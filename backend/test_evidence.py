import json
from app.main import app, get_evidence, verify_evidence
from app.database import init_db

init_db()

print('Evidence initialized')
ev = get_evidence()
print(f'Total evidence records: {len(ev)}')
if ev:
    evi_id = ev[0]["id"]
    print(f'Verifying record ID: {evi_id}')
    res = verify_evidence(evi_id)
    print(json.dumps(res, indent=2))
