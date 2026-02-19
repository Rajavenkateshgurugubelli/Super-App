import unittest
import sys
import os
import time
import uuid

# Add root to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'app'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User, Wallet, Transaction
from app.services.user_service import UserService
from app.services.wallet_service import WalletService
from app import user_pb2, wallet_pb2

# Use in-memory SQLite for testing logic unrelated to finding the file
TEST_DATABASE_URL = "sqlite:///:memory:"

class TestPersistence(unittest.TestCase):
    def setUp(self):
        # Setup Test DB
        self.engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Monkey patch the SessionLocal imported in services
        # Because 'from app.database import SessionLocal' creates a copy of the reference in the service module
        import app.services.user_service
        import app.services.wallet_service
        
        app.services.user_service.SessionLocal = self.SessionLocal
        app.services.wallet_service.SessionLocal = self.SessionLocal

        self.user_service = UserService()
        self.wallet_service = WalletService()

    def test_full_flow(self):
        # 1. Create User
        user_req = user_pb2.CreateUserRequest(email=f"test{uuid.uuid4()}@example.com", name="Integration User", region=user_pb2.REGION_US)
        user_resp = self.user_service.CreateUser(user_req, None)
        user_id = user_resp.user.user_id
        self.assertTrue(user_id)

        # 2. Create Wallet
        wallet_req = wallet_pb2.CreateWalletRequest(user_id=user_id, currency=wallet_pb2.CURRENCY_USD)
        wallet_resp = self.wallet_service.CreateWallet(wallet_req, None)
        wallet_id_1 = wallet_resp.wallet.wallet_id
        
        wallet_req_2 = wallet_pb2.CreateWalletRequest(user_id=user_id, currency=wallet_pb2.CURRENCY_USD)
        wallet_resp_2 = self.wallet_service.CreateWallet(wallet_req_2, None)
        wallet_id_2 = wallet_resp_2.wallet.wallet_id

        # 3. Manually fund wallet 1 (since we don't have Deposit endpoint yet)
        db = self.SessionLocal()
        w1 = db.query(Wallet).filter(Wallet.wallet_id == wallet_id_1).first()
        w1.balance = 500.0
        db.commit()
        db.close()

        # 4. Transfer Funds
        transfer_req = wallet_pb2.TransferFundsRequest(
            from_wallet_id=wallet_id_1,
            to_wallet_id=wallet_id_2,
            amount=100.0
        )
        transfer_resp = self.wallet_service.TransferFunds(transfer_req, None)
        self.assertTrue(transfer_resp.success)

        # 5. Verify Balances
        bal_resp_1 = self.wallet_service.GetBalance(wallet_pb2.GetBalanceRequest(wallet_id=wallet_id_1), None)
        bal_resp_2 = self.wallet_service.GetBalance(wallet_pb2.GetBalanceRequest(wallet_id=wallet_id_2), None)

        self.assertEqual(bal_resp_1.wallet.balance, 400.0)
        self.assertEqual(bal_resp_2.wallet.balance, 100.0)

if __name__ == '__main__':
    unittest.main()
