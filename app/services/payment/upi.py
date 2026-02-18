import logging
import uuid
import time

class UpiService:
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def initiate_payment(self, vpa, amount):
        self._logger.info(f"Initiating UPI payment for VPA: {vpa}, Amount: {amount}")
        # Simulate NPCI API call
        time.sleep(0.5) 
        if "fail" in vpa:
            return {"status": "FAILED", "txn_id": None}
        return {"status": "SUCCESS", "txn_id": f"UPI-{uuid.uuid4()}"}

    def verify_vpa(self, vpa):
        self._logger.info(f"Verifying VPA: {vpa}")
        return True
