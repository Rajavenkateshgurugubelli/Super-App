"""Run this script inside the backend container to add is_admin column to existing DB."""
from app.database import engine
from sqlalchemy import text, inspect

inspector = inspect(engine)
columns = [c['name'] for c in inspector.get_columns('users')]

if 'is_admin' in columns:
    print("Column 'is_admin' already exists — nothing to do.")
else:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0"))
        conn.commit()
    print("Column 'is_admin' added successfully.")

# Mark admin user
from app.database import SessionLocal
from app.models import User
session = SessionLocal()
try:
    admin = session.query(User).filter(User.email == "admin@abc.com").first()
    if admin:
        admin.is_admin = True
        session.commit()
        print(f"Admin user '{admin.name}' flagged as is_admin=True")
    else:
        print("Admin user not found in DB; run create_admin first.")
finally:
    session.close()
