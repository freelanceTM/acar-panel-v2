import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 1. Register dealer
r = client.post("/api/auth/register", json={"username": "dealer1", "password": "password123", "email": "d@example.com"})
print("Register:", r.status_code, r.json().get("username"))

# 2. Login
r = client.post("/api/auth/login", json={"username": "dealer1", "password": "password123"})
print("Login:", r.status_code)
cookie = r.cookies.get("access_token")
print("Cookie set:", bool(cookie))

# 3. Get me
r = client.get("/api/dealer/me", cookies={"access_token": cookie})
print("Me:", r.status_code, r.json().get("username"))

# 4. Create source
r = client.post("/api/dealer/sources", json={"name": "TestSrc", "url": "https://example.com/sub.txt"}, cookies={"access_token": cookie})
print("Source:", r.status_code, r.json().get("name"))

# 5. Create key
r = client.post("/api/dealer/keys", json={"client_name": "Ivan", "device_limit": 2}, cookies={"access_token": cookie})
print("Key:", r.status_code)
key = r.json()
print("  Token:", key.get("token"))

# 6. Fetch subscription (should be empty since no real source, but should not crash)
r = client.get(f"/sub/{key['token']}", headers={"User-Agent": "Test/1.0"})
print("Sub:", r.status_code, r.headers.get("profile-title"))

# 7. Health
r = client.get("/api/health")
print("Health:", r.status_code, r.json())

print("\nAll tests passed.")
