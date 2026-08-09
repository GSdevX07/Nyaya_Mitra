import json
from app.main import app, get_evidence, verify_evidence
from app.database import init_db

init_db()

print('Evidence initialized')
ev = get_evidence()
print(f'Total evidence records: {len(ev)}')
tampered = [e for e in ev if e['case_id'] == 'UTP-0012' and 'remand' in e['title'].lower()][0]
print(f'Tampered record ID: {tampered["id"]}')
print('Verifying tampered record...')
res = verify_evidence(tampered['id'])
print(json.dumps(res, indent=2))

print('Verifying normal record...')
normal = [e for e in ev if e['case_id'] == 'UTP-0001' and 'remand' in e['title'].lower()][0]
res_normal = verify_evidence(normal['id'])
print(json.dumps(res_normal, indent=2))
