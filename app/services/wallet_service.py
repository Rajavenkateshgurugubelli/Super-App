import logging
import uuid
from app import wallet_pb2
from app import wallet_pb2_grpc

class WalletService(wallet_pb2_grpc.WalletServiceServicer):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def CreateWallet(self, request, context):
        self._logger.info(f"Creating wallet for user: {request.user_id}")
        return wallet_pb2.CreateWalletResponse(
            wallet=wallet_pb2.Wallet(
                wallet_id=str(uuid.uuid4()),
                user_id=request.user_id,
                currency=request.currency,
                balance=0.0
            )
        )

    def GetBalance(self, request, context):
        self._logger.info(f"Getting balance for wallet: {request.wallet_id}")
        return wallet_pb2.GetBalanceResponse(
            wallet=wallet_pb2.Wallet(
                wallet_id=request.wallet_id,
                balance=1000.00, # Mock balance
                currency=wallet_pb2.CURRENCY_USD
            )
        )

    def TransferFunds(self, request, context):
        self._logger.info(f"Transferring {request.amount} from {request.from_wallet_id} to {request.to_wallet_id}")
        return wallet_pb2.TransferFundsResponse(
            success=True,
            transaction_id=str(uuid.uuid4()),
            message="Transfer successful"
        )
