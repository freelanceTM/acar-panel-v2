import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, engine, Base
from app.models import User, UnlimitedSource, ClientKey, ServerConfig
from app.auth import get_password_hash
from app.tasks import fetch_single_source
import base64

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    # Create dealer
    dealer = db.query(User).filter(User.username == "testdealer").first()
    if not dealer:
        dealer = User(
            username="testdealer",
            email="test@test.com",
            hashed_password=get_password_hash("password123"),
            is_dealer=True,
            is_active=True,
            profile_title="Premium Access",
            announcement="Welcome, {USERNAME}!",
            server_name_template="{USERNAME} | {NUMBER}",
        )
        db.add(dealer)
        db.commit()
        db.refresh(dealer)
        print(f"Created dealer id={dealer.id}")
    else:
        print(f"Using existing dealer id={dealer.id}")

    # Add real source
    url = "https://example.com/sub.txt"  # ЗАМЕНИТЕ НА ВАШ РЕАЛЬНЫЙ URL
    source = db.query(UnlimitedSource).filter(UnlimitedSource.url == url).first()
    if not source:
        source = UnlimitedSource(url=url, name="Real VIP Sub", owner_id=dealer.id, is_active=True)
        db.add(source)
        db.commit()
        db.refresh(source)
        print(f"Created source id={source.id}")
    else:
        print(f"Using existing source id={source.id}")

    # Fetch now
    print("Fetching source...")
    fetch_single_source(source.id)

    servers = db.query(ServerConfig).filter(ServerConfig.source_id == source.id).all()
    print(f"\nParsed {len(servers)} servers:")
    for s in servers:
        print(f"  [{s.id}] {s.protocol.upper()} {s.host}:{s.port} | name='{s.server_name}'")

    # Create key
    key = ClientKey(dealer_id=dealer.id, client_name="Azamat", device_limit=3, is_active=True)
    db.add(key)
    db.commit()
    db.refresh(key)
    print(f"\nCreated key token={key.token}")

    # Test subscription output
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get(f"/sub/{key.token}", headers={"User-Agent": "Test/1.0"})
    print(f"\nSubscription request: {r.status_code}")
    print(f"Profile title header: {r.headers.get('profile-title')}")
    # Decode base64 content
    decoded = base64.b64decode(r.text).decode("utf-8")
    lines = decoded.splitlines()
    print(f"Lines in output: {len(lines)}")
    print("First 10 lines:")
    for line in lines[:10]:
        print("  ", line[:120])

    # Verify SS link preserved
    ss_lines = [l for l in lines if l.startswith("ss://")]
    print(f"\nSS links preserved: {len(ss_lines)}")
    vless_lines = [l for l in lines if l.startswith("vless://")]
    print(f"VLESS links preserved: {len(vless_lines)}")
    trojan_lines = [l for l in lines if l.startswith("trojan://")]
    print(f"Trojan links preserved: {len(trojan_lines)}")

    # Verify {USERNAME} replacement
    has_azamat = any("Azamat" in l for l in lines)
    print(f"\nUsername replacement works: {has_azamat}")

    # Verify headers
    has_title = any("profile-title" in l for l in lines)
    has_announce = any("announce" in l for l in lines)
    print(f"Profile-title header present: {has_title}")
    print(f"Announce header present: {has_announce}")

finally:
    db.close()
