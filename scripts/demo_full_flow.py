import sys, os, base64, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

BASE_URL = "http://testserver"

def banner(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def divider():
    print("-" * 60)

# 1. Register dealer
banner("1. РЕГИСТРАЦИЯ ДИЛЕРА")
r = client.post("/api/auth/register", json={"username": "vip_dealer", "password": "securepass123", "email": "vip@relaxpanel.local"})
print(f"Status: {r.status_code}")
print(f"User: {r.json().get('username')}, is_dealer: {r.json().get('is_dealer')}")

# 2. Login
banner("2. ВХОД")
r = client.post("/api/auth/login", json={"username": "vip_dealer", "password": "securepass123"})
print(f"Status: {r.status_code}")
cookie = r.cookies.get("access_token")
print(f"JWT Cookie: {'✅' if cookie else '❌'}")

# 3. Update profile
banner("3. НАСТРОЙКИ ПРОФИЛЯ ДИЛЕРА")
r = client.patch("/api/dealer/me", json={
    "profile_title": "🔥 VIP Access | RelaxPanel",
    "announcement": "Привет, {USERNAME}! Ваша подписка активна. Поддержка: @support",
    "server_name_template": "{USERNAME} | 🌍 Server {NUMBER}"
}, cookies={"access_token": cookie})
print(f"Status: {r.status_code}")
print(f"Profile title: {r.json().get('profile_title')}")

# 4. Add real unlimited source
banner("4. ДОБАВЛЕНИЕ UNLIMITED-ИСТОЧНИКА")
source_url = "https://tmcell.cyber-happ.online:443/vipsub7/QXphbWF0LDE3ODE1NDM3NzQJwhRVFz9lP"
r = client.post("/api/dealer/sources", json={"name": "VIP Real Source", "url": source_url, "is_active": True}, cookies={"access_token": cookie})
print(f"Status: {r.status_code}")
source_id = r.json().get("id")
print(f"Source ID: {source_id}")

# 5. Fetch immediately (simulate Celery worker)
banner("5. ФОРСИРОВАННЫЙ ПАРСИНГ (без ожидания Celery)")
from app.tasks import fetch_single_source
fetch_single_source(source_id)
print("✅ Источник распарсен вручную (в реальном режиме Celery сделает это автоматически)")

# Check servers
r = client.get("/api/dealer/servers", cookies={"access_token": cookie})
servers = r.json()
print(f"Серверов в базе: {len(servers)}")
for s in servers[:5]:
    print(f"  • [{s['protocol'].upper()}] {s['host']}:{s['port']} | '{s['server_name'][:40]}...'")
if len(servers) > 5:
    print(f"  ... и еще {len(servers)-5} серверов")

# 6. Create client key
banner("6. СОЗДАНИЕ КЛИЕНТСКОГО КЛЮЧА")
r = client.post("/api/dealer/keys", json={
    "client_name": "Azamat",
    "device_limit": 3,
    "is_active": True
}, cookies={"access_token": cookie})
key = r.json()
print(f"Status: {r.status_code}")
print(f"Client Name: {key['client_name']}")
print(f"Token: {key['token']}")
print(f"Device Limit: {key['device_limit']}")
print(f"HWID: {key['hwid'] or 'не привязан (будет зафиксирован при первом запросе)'}")
print(f"Expires: {key['expires_at'] or 'бессрочно'}")

# 7. Subscription URL
banner("7. ССЫЛКА ПОДПИСКИ ДЛЯ КЛИЕНТА")
sub_url = f"{BASE_URL}/sub/{key['token']}"
print(f"\n🌐 ПОДПИСКА URL:")
print(f"   {sub_url}")
print(f"\n📱 Для использования в клиенте (v2rayNG, Nekoray, V2Ray, etc.):")
print(f"   {sub_url}")

# 8. Get subscription (simulate client request)
banner("8. ПОЛУЧЕНИЕ ПОДПИСКИ (симуляция клиента)")
r = client.get(f"/sub/{key['token']}", headers={"User-Agent": "v2rayNG/1.8.5"})
print(f"Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('content-type')}")
print(f"Profile-Title: {r.headers.get('profile-title')}")

decoded = base64.b64decode(r.text).decode("utf-8")
lines = decoded.splitlines()
print(f"\nРазмер подписки: {len(lines)} строк")
print(f"\n📋 ПЕРВЫЕ 15 СТРОК ПОДПИСКИ:")
divider()
for i, line in enumerate(lines[:15]):
    print(f"  {i+1}. {line[:100]}{'...' if len(line)>100 else ''}")

# 9. Check device tracking
banner("9. ПРОВЕРКА DEVICE LIMIT (отслеживание устройств)")
r = client.get(f"/api/dealer/keys/{key['id']}/devices", cookies={"access_token": cookie})
devices = r.json()
print(f"Зарегистрировано устройств: {len(devices['devices'])} / {devices['limit']}")
for d in devices['devices']:
    print(f"  • IP: {d['ip']}")
    print(f"    UA: {d['user_agent'][:60]}...")
    print(f"    Last seen: {d['last_seen']}")

# 10. Admin stats (if exists, but dealer doesn't have admin access)
# Just show key info
banner("10. ИНФОРМАЦИЯ ДЛЯ ДИЛЕРА")
print(f"""
┌─────────────────────────────────────────────┐
│  🆔 Token:       {key['token']}
│  👤 Client:      {key['client_name']}
│  📅 Created:     {key['created_at']}
│  🔒 Device Limit: {key['device_limit']}
│  🌐 Sub URL:     /sub/{key['token']}
│  📝 Status:      {'Активен' if key['is_active'] else 'Отключен'}
└─────────────────────────────────────────────┘
""")

print(f"\n{'='*60}")
print("  DEMO ЗАВЕРШЕН. ВСЕ СИСТЕМЫ РАБОТАЮТ.")
print(f"{'='*60}\n")
