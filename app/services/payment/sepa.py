import logging
import uuid
import time

class SepaService:
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def initiate_sct(self, iban, amount):
        self._logger.info(f"Initiating SEPA Credit Transfer for IBAN: {iban}, Amount: {amount}")
        # Simulate PSD2 API call
        time.sleep(0.8)
        return {"status": "PENDING", "txn_id": f"SEPA-{uuid.uuid4()}"}

    def check_iban(self, iban):
        self._logger.info(f"Checking IBAN validity: {iban}")
        return True
