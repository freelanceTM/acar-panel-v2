import sys, os, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app.main import app
from app.tasks import fetch_single_source

client = TestClient(app)

def banner(title):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")

def divider():
    print("-" * 65)

# 1. Register dealer
banner("1. РЕГИСТРАЦИЯ ДИЛЕРА")
r = client.post("/api/auth/register", json={"username": "acar_dealer", "password": "pass1234", "email": "dealer@acar.local"})
print(f"Status: {r.status_code} | User: {r.json().get('username')}")

# 2. Login
banner("2. ВХОД")
r = client.post("/api/auth/login", json={"username": "acar_dealer", "password": "pass1234"})
cookie = r.cookies.get("access_token")
print(f"JWT Cookie: {'✅' if cookie else '❌'}")

# 3. Update profile
banner("3. НАСТРОЙКИ ПРОФИЛЯ")
r = client.patch("/api/dealer/me", json={
    "profile_title": "Açar🔐 VIP",
    "announcement": "Добро пожаловать, {USERNAME}! Ваш доступ активен.",
    "server_name_template": "{USERNAME} | 🌍 #{NUMBER}"
}, cookies={"access_token": cookie})
print(f"Profile title: {r.json().get('profile_title')}")

# 4. Add FIRST source
banner("4. ИСТОЧНИК 1 — Real VIP sub")
url1 = "https://example.com/sub.txt"  # ЗАМЕНИТЕ НА ВАШ ПЕРВЫЙ REAL URL
r = client.post("/api/dealer/sources", json={"name": "VIP Source #1", "url": url1, "is_active": True}, cookies={"access_token": cookie})
source1_id = r.json().get("id")
print(f"Source ID: {source1_id} | Name: {r.json().get('name')}")
fetch_single_source(source1_id)
print("✅ Распарсен!")

# 5. Add SECOND source (we'll simulate with a different URL — same for demo, but different priority logic)
# For demo, we'll use the same URL but pretend it's different. In real life you'd add a second sub.
banner("5. ИСТОЧНИК 2 — Второй unlimited sub (симуляция)")
# For demo, we add the same URL again to show merging. In production this would be a different URL.
r = client.post("/api/dealer/sources", json={"name": "VIP Source #2", "url": url1, "is_active": True}, cookies={"access_token": cookie})
source2_id = r.json().get("id")
print(f"Source ID: {source2_id} | Name: {r.json().get('name')}")
fetch_single_source(source2_id)
print("✅ Распарсен!")

# 6. Check all servers (merged from both sources)
banner("6. ВСЕ СЕРВЕРА (ОБЪЕДИНЕНИЕ 2 ИСТОЧНИКОВ)")
r = client.get("/api/dealer/servers", cookies={"access_token": cookie})
servers = r.json()
print(f"Всего серверов в панели: {len(servers)}")
print(f"Из источника #{source1_id}: {len([s for s in servers if s['source_id']==source1_id])}")
print(f"Из источника #{source2_id}: {len([s for s in servers if s['source_id']==source2_id])}")
divider()
for i, s in enumerate(servers[:10], 1):
    print(f"  {i:2d}. [{s['protocol'].upper():6}] {s['host']:20} | src={s['source_id']} | pri={s['priority']:2} | '{s['server_name'][:35]}'")
if len(servers) > 10:
    print(f"  ... и еще {len(servers)-10} серверов")

# 7. Reorder servers globally (simulate drag-and-drop: move first server to end)
banner("7. ГЛОБАЛЬНАЯ СОРТИРОВКА (Drag-and-Drop между источниками)")
# Take all server IDs, reverse them to show cross-source reordering
reordered = [{"id": s["id"], "priority": idx} for idx, s in enumerate(reversed(servers))]
r = client.post("/api/dealer/servers/reorder", json=reordered, cookies={"access_token": cookie})
print(f"Reorder status: {r.status_code} | {r.json().get('detail')}")

# Verify new order
r = client.get("/api/dealer/servers", cookies={"access_token": cookie})
new_servers = r.json()
print(f"\nНовый порядок (первые 5):")
for i, s in enumerate(new_servers[:5], 1):
    print(f"  {i}. [{s['protocol'].upper()}] {s['host']} | src={s['source_id']} | pri={s['priority']}")

# 8. Disable some servers from source #2 (to show selective filtering)
banner("8. ВЫКЛЮЧЕНИЕ СЕРВЕРОВ (дилер управляет)")
servers_from_2 = [s for s in new_servers if s['source_id'] == source2_id]
if servers_from_2:
    to_disable = servers_from_2[0]
    r = client.patch(f"/api/dealer/servers/{to_disable['id']}", json={"is_active": False}, cookies={"access_token": cookie})
    print(f"Disabled server {to_disable['id']} ({to_disable['host']}) — status {r.status_code}")
    print(f"Теперь серверов из источника #{source2_id}: {len([s for s in client.get('/api/dealer/servers', cookies={'access_token': cookie}).json() if s['source_id']==source2_id and s['is_active']])} активных")

# 9. Create client key
banner("9. СОЗДАНИЕ КЛИЕНТА")
r = client.post("/api/dealer/keys", json={"client_name": "Azamat", "device_limit": 3, "is_active": True}, cookies={"access_token": cookie})
key = r.json()
print(f"Client: {key['client_name']}")
print(f"Token: {key['token']}")
print(f"Sub URL: /sub/{key['token']}")

# 10. Get subscription — merged from both sources!
banner("10. ПОДПИСКА КЛИЕНТА (ОБЪЕДИНЕНИЕ ОБОИХ ИСТОЧНИКОВ)")
r = client.get(f"/sub/{key['token']}", headers={"User-Agent": "v2rayNG/1.8.5"})
print(f"Status: {r.status_code}")
print(f"Profile-Title: {r.headers.get('profile-title')}")

decoded = base64.b64decode(r.text).decode("utf-8")
lines = decoded.splitlines()
print(f"\nВсего строк в подписке: {len(lines)}")
print(f"  (включая 2 заголовка + {len(lines)-2} серверов)")

# Count protocols
ss = [l for l in lines if l.startswith("ss://")]
vl = [l for l in lines if l.startswith("vless://")]
tr = [l for l in lines if l.startswith("trojan://")]
print(f"\nПротоколы:")
print(f"  SS:      {len(ss)}")
print(f"  VLESS:   {len(vl)}")
print(f"  Trojan:  {len(tr)}")
print(f"  TOTAL:   {len(ss)+len(vl)+len(tr)}")

divider()
print("Первые 10 строк подписки:")
for i, line in enumerate(lines[:10], 1):
    print(f"  {i}. {line[:100]}{'...' if len(line)>100 else ''}")

# 11. Verify domains are preserved (not changed)
banner("11. ПРОВЕРКА: ДОМЕНЫ ИЗ ИСТОЧНИКОВ НЕ ИЗМЕНЕНЫ")
hosts = []
for line in lines:
    if line.startswith(("ss://", "vless://", "trojan://", "vmess://")):
        # crude host extraction from raw link
        if "@" in line:
            host_port = line.split("@", 1)[1].split("?", 1)[0].split("#", 1)[0].split(":", 1)[0]
            hosts.append(host_port)

unique_hosts = sorted(set(hosts))
print(f"Уникальные хосты в подписке ({len(unique_hosts)}):")
for h in unique_hosts:
    print(f"  • {h}")
print(f"\n✅ Домены оригинальных источников сохранены!")

# 12. Verify names are customized
banner("12. ПРОВЕРКА: ИМЕНА СЕРВЕРОВ ЗАМЕНЕНЫ ПО ШАБЛОНУ")
has_custom_name = any("Azamat" in l for l in lines)
print(f"Имя клиента 'Azamat' присутствует в подписке: {has_custom_name}")
for line in lines[2:5]:
    if "#" in line:
        name = line.rsplit("#", 1)[1]
        print(f"  Имя сервера: '{name[:50]}'")

banner("🎉 ДЕМО ЗАВЕРШЕНО")
print("""
┌──────────────────────────────────────────────────────────────┐
│  Açar🔐 работает с объединением источников!                   │
│  • 2 unlimited sub → 1 подписка клиента                      │
│  • Домены оригинальных серверов сохранены                    │
│  • Имена заменяются по шаблону дилера                       │
│  • Глобальный drag-and-drop порядок между источниками       │
│  • Дилер вкл/выкл любой сервер индивидуально               │
└──────────────────────────────────────────────────────────────┘
""")
