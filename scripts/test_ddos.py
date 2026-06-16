import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Create a key first
r = client.post("/api/auth/register", json={"username": "ddos_test", "password": "pass1234"})
r = client.post("/api/auth/login", json={"username": "ddos_test", "password": "pass1234"})
cookie = r.cookies.get("access_token")
r = client.post("/api/dealer/keys", json={"client_name": "Test", "device_limit": 10}, cookies={"access_token": cookie})
token = r.json()["token"]

print(f"Token: {token}")
print("\nFiring 150 requests to /sub/{token}...")

blocked = 0
ok = 0
for i in range(150):
    r = client.get(f"/sub/{token}", headers={"User-Agent": "Test/1.0"})
    if r.status_code == 429:
        blocked += 1
    elif r.status_code == 200:
        ok += 1
    if i % 30 == 0:
        print(f"  Request {i}: {r.status_code}")

print(f"\n✅ 200 OK: {ok}")
print(f"🚫 429 Blocked: {blocked}")
print(f"\nDDoS protection: {'ACTIVE' if blocked > 0 else 'NOT TRIGGERED (may need more requests)'}")
