"""Create the first administrator from a trusted local shell, never a public endpoint."""
import getpass
import sys

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.entities import User


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python create_admin.py admin@example.edu")
    email = sys.argv[1].strip().lower()
    password = getpass.getpass("New admin password (10+ chars): ")
    if len(password) < 10:
        raise SystemExit("Password must contain at least 10 characters")
    db = SessionLocal()
    try:
        if db.query(User).filter_by(email=email).first():
            raise SystemExit("An account already uses that email")
        db.add(User(email=email, password_hash=hash_password(password), role="admin"))
        db.commit()
    finally:
        db.close()
    print("Administrator account created")


if __name__ == "__main__":
    main()
