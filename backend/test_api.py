from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User

client = TestClient(app)
db = SessionLocal()

# Find the test user
user = db.query(User).filter(User.email.like('%test%')).first()
if not user:
    user = db.query(User).first()

# Create an access token for them
from app.utils.security import create_access_token
token = create_access_token({"sub": user.id})

headers = {"Authorization": f"Bearer {token}"}
group_id = "45fab360-a8c4-4f58-ba1a-68bdc705bf01"

# 1. Fetch expenses
res = client.get(f"/api/groups/{group_id}/expenses", headers=headers)
print("--- EXPENSES API ---")
import json
print(json.dumps(res.json(), indent=2))

# 2. Fetch balances
res = client.get(f"/api/groups/{group_id}/balances", headers=headers)
print("--- BALANCES API ---")
print(json.dumps(res.json(), indent=2))
