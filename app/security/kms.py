import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Mock Master Key (In production, this is inside the HSM/KMS)
# We store it in an environment variable for the demo
MASTER_KEY_HEX = os.environ.get("SUPER_APP_MASTER_KEY", "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff")

class KMSMock:
    """
    Simulates a cloud KMS (AWS KMS / Google Cloud KMS)
    In a real system, the 'master_key' never leaves the service.
    """
    def __init__(self):
        self.key = bytes.fromhex(MASTER_KEY_HEX)
        self.aesgcm = AESGCM(self.key)

    def encrypt_dek(self, dek: bytes) -> str:
        """Encrypts a Data Encryption Key (DEK) for storage."""
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, dek, None)
        # Combine nonce and ciphertext
        return base64.b64encode(nonce + ciphertext).decode('utf-8')

    def decrypt_dek(self, encrypted_dek_str: str) -> bytes:
        """Decrypts a stored DEK using the Master Key."""
        data = base64.b64decode(encrypted_dek_str)
        nonce = data[:12]
        ciphertext = data[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None)

    def generate_dek(self) -> tuple[bytes, str]:
        """Generates a new DEK and its encrypted version."""
        dek = os.urandom(32) # AES-256
        encrypted_dek = self.encrypt_dek(dek)
        return dek, encrypted_dek

def encrypt_field(dek: bytes, plaintext: str) -> str:
    """Standard field-level encryption using AES-GCM."""
    if not plaintext: return ""
    aesgcm = AESGCM(dek)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode('utf-8')

def decrypt_field(dek: bytes, ciphertext_str: str) -> str:
    """Standard field-level decryption."""
    if not ciphertext_str: return ""
    try:
        aesgcm = AESGCM(dek)
        data = base64.b64decode(ciphertext_str)
        nonce = data[:12]
        ciphertext = data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
    except Exception:
        return "[ENCRYPTION_ERROR]"

kms = KMSMock()
