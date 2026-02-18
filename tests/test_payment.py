import unittest
import sys
import os

# Add root to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'app'))

from app.services.payment.upi import UpiService
from app.services.payment.sepa import SepaService

class TestPaymentServices(unittest.TestCase):
    def setUp(self):
        self.upi = UpiService()
        self.sepa = SepaService()

    def test_upi_success(self):
        result = self.upi.initiate_payment("user@upi", 100.0)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertTrue(result["txn_id"].startswith("UPI-"))

    def test_upi_failure(self):
        result = self.upi.initiate_payment("fail@upi", 100.0)
        self.assertEqual(result["status"], "FAILED")
        self.assertIsNone(result["txn_id"])

    def test_sepa_initiation(self):
        result = self.sepa.initiate_sct("DE1234567890", 500.0)
        self.assertEqual(result["status"], "PENDING")
        self.assertTrue(result["txn_id"].startswith("SEPA-"))

if __name__ == '__main__':
    unittest.main()
