import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, engine, Base
from app.models import User
from app.auth import get_password_hash

Base.metadata.create_all(bind=engine)

def create_admin(username: str, password: str):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.is_admin = True
        user.is_dealer = True
        user.hashed_password = get_password_hash(password)
        print(f"Updated existing user {username} to admin")
    else:
        user = User(
            username=username,
            email=f"{username}@admin.local",
            hashed_password=get_password_hash(password),
            is_admin=True,
            is_dealer=True,
            is_active=True,
        )
        db.add(user)
        print(f"Created admin {username}")
    db.commit()
    db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password>")
        sys.exit(1)
    create_admin(sys.argv[1], sys.argv[2])
