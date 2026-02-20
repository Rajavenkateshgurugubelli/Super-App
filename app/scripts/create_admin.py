from app.database import SessionLocal
from app.models import User, Region, KycStatus, Wallet, Currency
from app.security import get_password_hash
import uuid

def create_admin():
    session = SessionLocal()
    try:
        email = "admin@abc.com"
        password_raw = "admin1"
        phone = "+11234567890"

        existing_user = session.query(User).filter(User.email == email).first()
        user_id = None

        if existing_user:
            print("Admin user already exists — ensuring is_admin=True...")
            existing_user.is_admin = True
            session.commit()
            user_id = existing_user.user_id
        else:
            print("Creating admin user...")
            user_id = str(uuid.uuid4())
            new_user = User(
                user_id=user_id,
                email=email,
                name="Admin User",
                region=Region.US,
                password_hash=get_password_hash(password_raw),
                kyc_status=KycStatus.VERIFIED,
                phone_number=phone,
                is_admin=True
            )
            session.add(new_user)
            session.commit()
            print("Admin user created successfully.")

        # Create wallet for admin if not exists
        existing_wallet = session.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not existing_wallet:
            print("Creating admin wallet...")
            new_wallet = Wallet(
                wallet_id=str(uuid.uuid4()),
                user_id=user_id,
                currency=Currency.USD,
                balance=10000.0
            )
            session.add(new_wallet)
            session.commit()
            print("Admin wallet created with $10,000 balance.")
        else:
            print(f"Admin wallet already exists (balance={existing_wallet.balance}).")

    except Exception as e:
        print(f"Error creating admin: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_admin()
