import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class EncryptionUtil:
    def __init__(self, key=None):
        # In a real app, this key should be loaded from a secure vault (e.g., AWS KMS, HashiCorp Vault)
        # For this prototype, we generate one if not provided or use a fixed one from env
        self.key = key or os.environ.get("ENCRYPTION_KEY", os.urandom(32))
        if isinstance(self.key, str):
             # Ensure key is bytes
             try:
                self.key = base64.b64decode(self.key)
             except:
                # If not base64, ensure it's 32 bytes or hash it
                if len(self.key) != 32:
                    # just a fallback for prototype clarity
                    import hashlib
                    self.key = hashlib.sha256(self.key.encode()).digest()
                else:
                    self.key = self.key.encode()

    def encrypt_pii(self, plaintext: str) -> str:
        iv = os.urandom(12) # GCM recommends 12 bytes IV
        encryptor = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv),
            backend=default_backend()
        ).encryptor()

        ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
        
        # Return IV + Tag + Ciphertext encoded in base64
        # Structure: IV (12) | Tag (16) | Ciphertext
        return base64.b64encode(iv + encryptor.tag + ciphertext).decode('utf-8')

    def decrypt_pii(self, payload: str) -> str:
        data = base64.b64decode(payload)
        iv = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]

        decryptor = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv, tag),
            backend=default_backend()
        ).decryptor()

        return (decryptor.update(ciphertext) + decryptor.finalize()).decode('utf-8')
