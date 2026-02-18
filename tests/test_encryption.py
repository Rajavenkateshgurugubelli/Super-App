import unittest
import sys
import os

# Add root to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'app'))

from app.utils.encryption import EncryptionUtil

class TestEncryptionUtil(unittest.TestCase):
    def setUp(self):
        self.encryption = EncryptionUtil()

    def test_encrypt_decrypt(self):
        original_text = "Sensitive PII Data: 123-456-7890"
        encrypted = self.encryption.encrypt_pii(original_text)
        
        self.assertNotEqual(original_text, encrypted)
        
        decrypted = self.encryption.decrypt_pii(encrypted)
        self.assertEqual(original_text, decrypted)

    def test_decrypt_invalid_tag(self):
        original_text = "Test Data"
        encrypted = self.encryption.encrypt_pii(original_text)
        
        # Tamper with the encrypted paylod (flip a bit in the tag)
        import base64
        data = bytearray(base64.b64decode(encrypted))
        data[15] ^= 1 # Tamper with tag area
        tampered = base64.b64encode(data).decode('utf-8')

        with self.assertRaises(Exception):
            self.encryption.decrypt_pii(tampered)

if __name__ == '__main__':
    unittest.main()
