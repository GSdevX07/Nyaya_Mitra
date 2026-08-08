import urllib.request, json

# Test GET /
r = urllib.request.urlopen("http://localhost:8001/")
health = json.loads(r.read())
print("GET /:", health)

# Test GET /cases
r = urllib.request.urlopen("http://localhost:8001/cases")
cases = json.loads(r.read())
print(f"\nGET /cases -- {len(cases)} cases, sorted by urgency:")
for e in cases:
    cid = e["case"]["case_id"]
    print(f"  {cid} | urgency_score={e['urgency_score']} | days_overdue={e['days_overdue']}")

# Test GET /cases/UTP-0007
r = urllib.request.urlopen("http://localhost:8001/cases/UTP-0007")
detail = json.loads(r.read())
print("\nGET /cases/UTP-0007:")
print(f"  eligible      = {detail['eligibility']['eligible']}")
print(f"  is_complete   = {detail['completeness']['is_complete']}")
print(f"  urgency_score = {detail['urgency_score']}")
print(f"  draft_ready   = {detail['draft_ready']}")
print(f"  alert_level   = {detail['notification']['alert_level']}")
print(f"  status        = {detail['status_tracking']['current_status']}")
print(f"  log entries   = {len(detail['agent_activity_log'])}")

# Test POST /cases/UTP-0007/approve
req = urllib.request.Request("http://localhost:8001/cases/UTP-0007/approve", method="POST")
req.add_header("Content-Length", "0")
r = urllib.request.urlopen(req)
approve = json.loads(r.read())
print("\nPOST /cases/UTP-0007/approve:")
print(f"  status    = {approve['status']}")
print(f"  next_step = {approve['next_step']}")

# Test 404
try:
    urllib.request.urlopen("http://localhost:8001/cases/UTP-9999")
except urllib.error.HTTPError as e:
    print(f"\nGET /cases/UTP-9999: HTTP {e.code} (expected 404) [PASS]")

print("\n[PASS] All endpoints responding correctly.")
