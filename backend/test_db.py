from fastapi.testclient import TestClient
from app.main import app, root
from app.auth.tokens import create_access_token
from app.auth.roles import Role

client = TestClient(app)

def _get_headers():
    token = create_access_token(
        subject="Legal Officer 104",
        role=Role.DLSA_OFFICER.value,
        org_id="org_dlsa_central",
    )
    return {"Authorization": f"Bearer {token}"}


def test_endpoints():
    print('Root:', root())

    cases_res = client.get("/cases", headers=_get_headers())
    assert cases_res.status_code == 200
    cases = cases_res.json()
    print(f'Total cases retrieved: {len(cases)}')

    av_res = client.get("/cases/available", headers=_get_headers())
    assert av_res.status_code == 200
    av_cases = av_res.json()
    print(f'Available cases: {len(av_cases)}')

    prof_res = client.get("/lawyer/profile", headers=_get_headers())
    assert prof_res.status_code == 200
    prof = prof_res.json()
    print(f'Profile cases taken: {prof["cases_taken"]}')

    rep_res = client.get("/reports", headers=_get_headers())
    assert rep_res.status_code == 200
    rep = rep_res.json()
    print(f'Reports overview: {rep["overview"]}')

if __name__ == "__main__":
    test_endpoints()
