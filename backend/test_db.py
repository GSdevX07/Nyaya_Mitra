import sys
import asyncio
from app.main import app, root, get_cases, get_available_cases, get_lawyer_profile, get_reports

def test_endpoints():
    print('Root:', root())
    
    cases = get_cases()
    print(f'Total cases retrieved: {len(cases)}')
    if cases:
        print(f'First case: {cases[0]["case"]["case_id"]} - Score: {cases[0]["urgency_score"]}')

    av_cases = get_available_cases()
    print(f'Available cases: {len(av_cases)}')

    prof = get_lawyer_profile()
    print(f'Profile cases taken: {prof["cases_taken"]}')

    rep = get_reports()
    print(f'Reports overview: {rep["overview"]}')

if __name__ == "__main__":
    test_endpoints()
