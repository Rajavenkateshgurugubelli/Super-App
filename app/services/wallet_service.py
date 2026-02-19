import logging
import uuid
import time
from app import wallet_pb2
from app import wallet_pb2_grpc
from app import policy_pb2
from app import policy_pb2_grpc
import grpc
from app.database import SessionLocal
from app.models import Wallet, Transaction, Currency, User, ConversionRate
from app import models

import json
from kafka import KafkaProducer
from kafka.errors import KafkaError
import os
import redis

class WalletService(wallet_pb2_grpc.WalletServiceServicer):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.producer = None
        self.redis_client = None
        
        # Redis Connection
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self._logger.info(f"Connected to Redis at {redis_url}")
        except Exception as e:
            self._logger.warning(f"Failed to connect to Redis: {e}. Caching/Locking disabled.")

        # Kafka Connection
        try:
            kafka_url = os.environ.get('KAFKA_BROKER_URL', 'localhost:29092')
            self.producer = KafkaProducer(
                bootstrap_servers=[kafka_url],
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                api_version=(0, 10, 1) 
            )
            self._logger.info(f"Connected to Kafka at {kafka_url}")
        except Exception as e:
            self._logger.warning(f"Failed to connect to Kafka: {e}. Events will not be emitted.")

    def _emit_event(self, topic, event_type, payload):
        if not self.producer:
            return
        try:
            message = {
                "event_type": event_type,
                "timestamp": time.time(),
                "payload": payload
            }
            self.producer.send(topic, value=message)
            self.producer.flush() # Ensure it's sent (blocking but safer for critical events in MVP)
            self._logger.info(f"Emitted event {event_type} to topic {topic}")
        except Exception as e:
            self._logger.error(f"Failed to emit event: {e}")

    # ... (other methods)

    # ... (other methods)

    def ListWallets(self, request, context):
        self._logger.info(f"Listing wallets for user: {request.user_id}")
        session = SessionLocal()
        try:
            wallets = session.query(Wallet).filter(Wallet.user_id == request.user_id).all()
            return wallet_pb2.ListWalletsResponse(
                wallets=[self._map_wallet_to_proto(w) for w in wallets]
            )
        except Exception as e:
            self._logger.error(f"Error listing wallets: {e}")
            raise
        finally:
            session.close()

    def GetBalance(self, request, context):
        self._logger.info(f"Getting balance for wallet: {request.wallet_id}")
        
        # Check Redis Cache
        cache_key = f"wallet:{request.wallet_id}:balance"
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    self._logger.info("Cache Hit")
                    data = json.loads(cached_data)
                    return wallet_pb2.GetBalanceResponse(
                        wallet=wallet_pb2.Wallet(
                            wallet_id=data['wallet_id'],
                            user_id=data['user_id'],
                            currency=data['currency'],
                            balance=data['balance']
                        )
                    )
            except Exception as e:
                self._logger.warning(f"Redis Cache Error: {e}")

        # Cache Miss - Query DB
        session = SessionLocal()
        try:
            wallet = session.query(Wallet).filter(Wallet.wallet_id == request.wallet_id).first()
            if not wallet:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Wallet not found")
                return wallet_pb2.GetBalanceResponse()

            # Cache Result
            if self.redis_client:
                try:
                    cache_data = {
                        "wallet_id": wallet.wallet_id,
                        "user_id": wallet.user_id,
                        "currency": wallet.currency.value,
                        "balance": wallet.balance
                    }
                    self.redis_client.set(cache_key, json.dumps(cache_data), ex=60) # TTL 60s
                except Exception as e:
                     self._logger.warning(f"Redis Set Error: {e}")

            return wallet_pb2.GetBalanceResponse(wallet=self._map_wallet_to_proto(wallet))
        finally:
            session.close()

    def TransferFunds(self, request, context):
        self._logger.info(f"Transferring {request.amount} from {request.from_wallet_id}")
        
        # Redis Lock (Phase 8.2)
        lock_key = f"lock:wallet:{request.from_wallet_id}"
        lock_acquired = False
        if self.redis_client:
            try:
                # Simple distributed lock (10s expiry)
                lock_acquired = self.redis_client.set(lock_key, "locked", nx=True, ex=10)
                if not lock_acquired:
                    return wallet_pb2.TransferFundsResponse(
                        success=False,
                        message="Wallet is busy. Please try again."
                    )
            except Exception as e:
                self._logger.warning(f"Redis Lock Error: {e}")

        session = SessionLocal()
        try:
            target_wallet_id = request.to_wallet_id
            
            # Resolve Phone Number if provided
            if not target_wallet_id and request.to_phone_number:
                self._logger.info(f"Resolving phone number: {request.to_phone_number}")
                recipient_user = session.query(User).filter(User.phone_number == request.to_phone_number).first()
                if not recipient_user:
                     return wallet_pb2.TransferFundsResponse(
                        success=False,
                        message="Recipient phone number not found"
                    )
                
                # Find a wallet for the user (Prefer same currency as sender if possible, else first found)
                # We need source wallet first to know currency
                source_wallet_check = session.query(Wallet).filter(Wallet.wallet_id == request.from_wallet_id).first()
                if not source_wallet_check:
                     return wallet_pb2.TransferFundsResponse(success=False, message="Source wallet not found")
                
                recipient_wallets = session.query(Wallet).filter(Wallet.user_id == recipient_user.user_id).all()
                if not recipient_wallets:
                     return wallet_pb2.TransferFundsResponse(success=False, message="Recipient has no wallets")
                
                # Try match currency
                target_wallet = next((w for w in recipient_wallets if w.currency == source_wallet_check.currency), recipient_wallets[0])
                target_wallet_id = target_wallet.wallet_id
                self._logger.info(f"Resolved to wallet: {target_wallet_id}")

            if not target_wallet_id:
                return wallet_pb2.TransferFundsResponse(success=False, message="Destination wallet ID or Phone Number required")

            # Transactional transfer
            source_wallet = session.query(Wallet).filter(Wallet.wallet_id == request.from_wallet_id).with_for_update().first()
            dest_wallet = session.query(Wallet).filter(Wallet.wallet_id == target_wallet_id).with_for_update().first()

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

            # Policy Check
            try:
                # We need the User's region.
                owner_user = session.query(User).filter(User.user_id == source_wallet.user_id).first()
                dest_owner = session.query(User).filter(User.user_id == dest_wallet.user_id).first()
                
                target_region_val = str(dest_owner.region.value) if dest_owner else "0"
                
                # Check Compliance
                policy_channel = grpc.insecure_channel('localhost:50051')
                policy_stub = policy_pb2_grpc.PolicyServiceStub(policy_channel)
                
                policy_req = policy_pb2.CheckComplianceRequest(
                    user_id=owner_user.user_id,
                    action="transfer_funds",
                    target_region=target_region_val
                )
                policy_resp = policy_stub.CheckCompliance(policy_req)
                
                if not policy_resp.allowed:
                     return wallet_pb2.TransferFundsResponse(
                         success=False, 
                         message=f"Policy Check Failed: {policy_resp.reason}"
                     )
                     
            except Exception as pe:
                self._logger.error(f"Policy Check Error: {pe}")
                # Fail open or closed? Security says closed.
                return wallet_pb2.TransferFundsResponse(success=False, message="Policy Service Unavailable")

            # Currency Conversion
            debit_amount = request.amount
            credit_amount = request.amount
            exchange_rate_value = 1.0
            
            if source_wallet.currency != dest_wallet.currency:
                exchange_rate_value = self._get_exchange_rate(source_wallet.currency, dest_wallet.currency)
                credit_amount = debit_amount * exchange_rate_value
                self._logger.info(f"Converting {debit_amount} {source_wallet.currency} to {credit_amount} {dest_wallet.currency} (Rate: {exchange_rate_value})")

            # Perform Transfer
            source_wallet.balance -= debit_amount
            dest_wallet.balance += credit_amount

            # Record Transaction
            txn_id = str(uuid.uuid4())
            txn = Transaction(
                transaction_id=txn_id,
                from_wallet_id=request.from_wallet_id,
                to_wallet_id=request.to_wallet_id,
                amount=debit_amount, 
                status="SUCCESS",
                timestamp=time.time()
            )
            session.add(txn)
            
            # Record Conversion Rate
            conv_rate = models.ConversionRate(
                transaction_id=txn_id,
                from_currency=str(source_wallet.currency.name),
                to_currency=str(dest_wallet.currency.name),
                rate=exchange_rate_value,
                timestamp=time.time()
            )
            session.add(conv_rate)
            
            session.commit()

            # Cache Invalidation (Phase 8.1)
            # Invalidate both source and destination balance caches
            if self.redis_client:
                try:
                    self.redis_client.delete(f"wallet:{request.from_wallet_id}:balance")
                    self.redis_client.delete(f"wallet:{target_wallet_id}:balance")
                except Exception as e:
                    self._logger.warning(f"Cache Invalidation Error: {e}")

            # Emit Event (Phase 7.2)
            self._emit_event("transactions", "TransactionInitiated", {
                "transaction_id": txn_id,
                "from_wallet": request.from_wallet_id,
                "to_wallet": target_wallet_id,
                "amount": request.amount,
                "currency": str(source_wallet.currency.name),
                "timestamp": time.time()
            })

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
            # Release Lock
            if lock_acquired and self.redis_client:
                try:
                    self.redis_client.delete(lock_key)
                except Exception as e:
                    self._logger.warning(f"Lock Release Error: {e}")

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

    def GetConversionHistory(self, request, context):
        self._logger.info(f"Getting conversion history for wallet: {request.wallet_id}")
        session = SessionLocal()
        try:
            # Join Transaction to filter by wallet_id
            # ConversionRate -> Transaction -> Wallet (from or to)
            
            # Helper subquery or join
            # We want all conversions where the associated transaction involves this wallet
            
            conversions = session.query(models.ConversionRate).join(models.Transaction).filter(
                (models.Transaction.from_wallet_id == request.wallet_id) | 
                (models.Transaction.to_wallet_id == request.wallet_id)
            ).order_by(models.ConversionRate.timestamp.desc()).all()
            
            records = []
            for c in conversions:
                records.append(wallet_pb2.ConversionRecord(
                    transaction_id=c.transaction_id,
                    from_currency=c.from_currency,
                    to_currency=c.to_currency,
                    rate=c.rate,
                    amount_original=c.transaction.amount, # This is the source amount
                    # We don't store converted amount in ConversionRate directly, but can derive or store it.
                    # For now, let's calculate it or add it to model?
                    # The prompt said "track rates used". 
                    # Let's just return rate * amount
                    amount_converted=c.transaction.amount * c.rate,
                    timestamp=c.timestamp
                ))
                
            return wallet_pb2.GetConversionHistoryResponse(records=records)
        except Exception as e:
             self._logger.error(f"Error getting conversion history: {e}")
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
