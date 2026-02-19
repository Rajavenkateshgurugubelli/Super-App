import logging
import uuid
import time
from app import wallet_pb2
from app import wallet_pb2_grpc
from app.database import SessionLocal
from app.models import Wallet, Transaction, Currency

class WalletService(wallet_pb2_grpc.WalletServiceServicer):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def CreateWallet(self, request, context):
        self._logger.info(f"Creating wallet for user: {request.user_id}")
        session = SessionLocal()
        try:
            new_wallet = Wallet(
                user_id=request.user_id,
                currency=Currency(request.currency),
                balance=0.0
            )
            session.add(new_wallet)
            session.commit()
            session.refresh(new_wallet)
            
            return wallet_pb2.CreateWalletResponse(
                wallet=self._map_wallet_to_proto(new_wallet)
            )
        except Exception as e:
            self._logger.error(f"Error creating wallet: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def GetBalance(self, request, context):
        self._logger.info(f"Getting balance for wallet: {request.wallet_id}")
        session = SessionLocal()
        try:
            wallet = session.query(Wallet).filter(Wallet.wallet_id == request.wallet_id).first()
            if not wallet:
                # Handle not found
                return wallet_pb2.GetBalanceResponse(
                    balance=0.0,
                    currency=wallet_pb2.CURRENCY_USD # Default
                )
            
            return wallet_pb2.GetBalanceResponse(
                wallet=self._map_wallet_to_proto(wallet)
            )
        finally:
            session.close()

    def TransferFunds(self, request, context):
        self._logger.info(f"Transferring {request.amount} from {request.from_wallet_id} to {request.to_wallet_id}")
        session = SessionLocal()
        try:
            # Transactional transfer
            source_wallet = session.query(Wallet).filter(Wallet.wallet_id == request.from_wallet_id).with_for_update().first()
            dest_wallet = session.query(Wallet).filter(Wallet.wallet_id == request.to_wallet_id).with_for_update().first()

            if not source_wallet or not dest_wallet:
                return wallet_pb2.TransferFundsResponse(
                    success=False,
                    transaction_id="",
                    message="One or both wallets not found"
                )

            if source_wallet.balance < request.amount:
                return wallet_pb2.TransferFundsResponse(
                    success=False,
                    transaction_id="",
                    message="Insufficient funds"
                )

            # Currency Conversion
            debit_amount = request.amount
            credit_amount = request.amount
            
            if source_wallet.currency != dest_wallet.currency:
                rate = self._get_exchange_rate(source_wallet.currency, dest_wallet.currency)
                credit_amount = debit_amount * rate
                self._logger.info(f"Converting {debit_amount} {source_wallet.currency} to {credit_amount} {dest_wallet.currency} (Rate: {rate})")

            # Perform Transfer
            source_wallet.balance -= debit_amount
            dest_wallet.balance += credit_amount

            # Record Transaction
            txn_id = str(uuid.uuid4())
            txn = Transaction(
                transaction_id=txn_id,
                from_wallet_id=request.from_wallet_id,
                to_wallet_id=request.to_wallet_id,
                amount=debit_amount, # Recording source amount
                status="SUCCESS",
                timestamp=time.time()
            )
            session.add(txn)
            
            session.commit()

            return wallet_pb2.TransferFundsResponse(
                success=True,
                transaction_id=txn_id,
                message="Transfer successful"
            )
        except Exception as e:
            self._logger.error(f"Transfer failed: {e}")
            session.rollback()
            return wallet_pb2.TransferFundsResponse(
                success=False,
                transaction_id="",
                message=f"Internal error: {str(e)}"
            )
        finally:
            session.close()

    def GetTransactionHistory(self, request, context):
        self._logger.info(f"Getting transaction history for wallet: {request.wallet_id}")
        session = SessionLocal()
        try:
            # Query transactions where wallet is sender or receiver
            transactions = session.query(Transaction).filter(
                (Transaction.from_wallet_id == request.wallet_id) | 
                (Transaction.to_wallet_id == request.wallet_id)
            ).order_by(Transaction.timestamp.desc()).limit(20).all()

            txn_protos = []
            for txn in transactions:
                txn_protos.append(wallet_pb2.TransactionInfo(
                    transaction_id=txn.transaction_id,
                    from_wallet_id=txn.from_wallet_id,
                    to_wallet_id=txn.to_wallet_id,
                    amount=txn.amount,
                    status=txn.status,
                    timestamp=txn.timestamp
                ))
            
            return wallet_pb2.GetTransactionHistoryResponse(transactions=txn_protos)
        except Exception as e:
            self._logger.error(f"Error getting history: {e}")
            raise
        finally:
            session.close()

    def _get_exchange_rate(self, from_currency, to_currency):
        # Base rates relative to USD (1.0)
        # USD=1, INR=2, EUR=3 (Enum values)
        # Let's map Enum to Logic
        # wallet_pb2.Currency.CURRENCY_USD is likely 1, etc.
        # We need to import or use the models enum, but models uses strings/enums mapped to DB.
        # Let's use the proto enum values for simplicity or map them.
        
        # Map Proto Enum -> Rate (USD Base)
        # CURRENCY_USD = 1
        # CURRENCY_INR = 2
        # CURRENCY_EUR = 3
        
        rates = {
            wallet_pb2.CURRENCY_USD: 1.0,
            wallet_pb2.CURRENCY_INR: 83.0,
            wallet_pb2.CURRENCY_EUR: 0.92
        }
        
        from_rate = rates.get(from_currency, 1.0)
        to_rate = rates.get(to_currency, 1.0)
        
        # Convert From -> USD -> To
        # Amount in USD = Amount / from_rate
        # Amount in To = (Amount / from_rate) * to_rate
        
        return to_rate / from_rate

    def _map_wallet_to_proto(self, wallet_model):
        return wallet_pb2.Wallet(
            wallet_id=wallet_model.wallet_id,
            user_id=wallet_model.user_id,
            currency=wallet_model.currency.value,
            balance=wallet_model.balance
        )
