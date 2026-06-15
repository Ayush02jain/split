import requests

API_URL = 'https://split-expense-backend-wvkv.onrender.com/api'

# 1. Register
r = requests.post(f'{API_URL}/auth/register', json={
    'email': 'tester100@example.com',
    'display_name': 'Tester',
    'password': 'password123'
})
token = r.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

# 2. Create Group
r = requests.post(f'{API_URL}/groups', json={
    'name': 'Test Group',
    'description': 'For testing import'
}, headers=headers)
group_id = r.json().get('id')

# 3. Upload CSV
with open('d:\\split\\expenses_export.csv', 'rb') as f:
    files = {'file': ('expenses_export.csv', f, 'text/csv')}
    r = requests.post(f'{API_URL}/groups/{group_id}/import/upload', files=files, headers=headers)
    session_id = r.json().get('id')

# 4. Get Preview
r = requests.get(f'{API_URL}/import/{session_id}/preview', headers=headers)
data = r.json()
print(f'Total Rows: {data.get("total_rows")}')
print(f'Anomalies: {len(data.get("anomalies", []))}')
print(f'To Review: {data.get("needs_review")}')
