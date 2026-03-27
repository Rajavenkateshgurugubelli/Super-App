import uuid
import time
import logging
from app.database import SessionLocal
from app.models import PaymentTokenStore, Region

logger = logging.getLogger("TokenizationService")

class TokenizationService:
    @staticmethod
    def tokenize_card(user_id: str, card_details: dict, region: Region) -> str:
        """
        Mocking a PCI-DSS vault. Stores metadata and returns a safe token.
        Details usually include: pan_last4, brand, exp_month, exp_year.
        """
        session = SessionLocal()
        try:
            # Generate a secure Vault ID (Mocking Stripe 'src_...' or 'pm_...')
            vault_id = f"pm_{uuid.uuid4().hex[:12]}"
            
            new_token = PaymentTokenStore(
                id=str(uuid.uuid4()),
                user_id=user_id,
                provider="internal_vault",
                provider_token=vault_id,
                last4=card_details.get("last4"),
                brand=card_details.get("brand"),
                method_type="CARD",
                region=region
            )
            
            session.add(new_token)
            session.commit()
            logger.info(f"Tokenized card for user {user_id} -> {vault_id}")
            return vault_id
        except Exception as e:
            logger.error(f"Tokenization failed: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def get_token_details(user_id: str, provider_token: str):
        session = SessionLocal()
        try:
            token = session.query(PaymentTokenStore).filter(
                PaymentTokenStore.user_id == user_id,
                PaymentTokenStore.provider_token == provider_token
            ).first()
            return token
        finally:
            session.close()

token_service = TokenizationService()
