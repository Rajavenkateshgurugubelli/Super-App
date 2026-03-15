import boto3
import base64
import json
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger("HSMSigner")
logger.setLevel(logging.INFO)

class HSMSigner:
    """
    Interfaces with AWS KMS (Hardware Security Module) to perform cryptographic
    signatures on W3C Verifiable Credentials without the private key ever
    leaving the physical HSM enclave.
    """
    def __init__(self, key_id: str, region_name: str = 'us-east-1'):
        self.key_id = key_id
        # In a real environment, boto3 resolves credentials from the IAM Role attached to the EKS Pod
        self.kms_client = boto3.client('kms', region_name=region_name)

    def sign_payload(self, payload: dict) -> str:
        """
        Takes a JSON payload, serializes it, and sends it to the HSM for signing using ECDSA.
        Returns the Base64 encoded signature.
        """
        try:
            message_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
            
            logger.info(f"Requesting HSM Signature for payload hash via Key {self.key_id}")
            
            # Request the HSM to sign the data
            response = self.kms_client.sign(
                KeyId=self.key_id,
                Message=message_bytes,
                MessageType='RAW',
                SigningAlgorithm='ECDSA_SHA_256'
            )
            
            signature_bytes = response['Signature']
            signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')
            
            logger.info("Successfully retrieved cryptographic signature from HSM.")
            return signature_b64
            
        except ClientError as e:
            logger.error(f"HSM Signing failed: {e.response['Error']['Message']}")
            raise

    def verify_signature(self, payload: dict, signature_b64: str) -> bool:
        """
        Verifies a signature using the public key derived from the HSM.
        """
        try:
            message_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
            signature_bytes = base64.b64decode(signature_b64)
            
            response = self.kms_client.verify(
                KeyId=self.key_id,
                Message=message_bytes,
                MessageType='RAW',
                Signature=signature_bytes,
                SigningAlgorithm='ECDSA_SHA_256'
            )
            
            return response.get('SignatureValid', False)
        except ClientError as e:
            logger.error(f"HSM Verification failed: {e.response['Error']['Message']}")
            return False

# Example usage (mocked out in local environments)
if __name__ == "__main__":
    # key_arn = "arn:aws:kms:us-east-1:123456789012:key/mrk-1234567890abcdef"
    # signer = HSMSigner(key_id=key_arn)
    # sig = signer.sign_payload({"did": "did:superapp:123", "kyc": True})
    # print(f"Hardware Signature: {sig}")
    pass
