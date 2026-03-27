import json
import time
from urllib.parse import urlencode

class UniversalQRService:
    """
    Standardizes QR code generation across UPI (India), EPC (Europe) and Super App Native DID.
    """
    
    def generate_cross_border_qr(self, user_id: str, did: str, region_id: int, amount: float = None):
        """
        Produces a 'Smart QR' payload that adapts based on the scanner's region.
        In the frontend, this is rendered as a QR code.
        """
        payload = {
            "ver": "3.0",
            "id": user_id,
            "did": did,
            "reg": region_id,
            "amt": amount,
            "ts": int(time.time()),
            # Add regional fallbacks for non-SuperApp scanners
            "fallbacks": []
        }
        
        # India Fallback (UPI intent)
        if region_id == 1: # India
            payload["fallbacks"].append({
                "type": "upi",
                "uri": self._get_upi_uri(did, amount)
            })
            
        # EU Fallback (EPC QR)
        if region_id == 2: # Europe
            payload["fallbacks"].append({
                "type": "epc",
                "uri": f"BCD\n002\n1\nSCT\n\nSUPERAPP\n{did}\nEUR{amount}\n\n\n"
            })
            
        return json.dumps(payload)

    def _get_upi_uri(self, did: str, amount: float) -> str:
        # Simulate mapping DID to VPA for interoperability
        vpa_alias = f"{did.split(':')[-1]}@superapp"
        params = {
            "pa": vpa_alias,
            "pn": "Super App Merchant",
            "am": str(amount or ""),
            "cu": "INR"
        }
        return f"upi://pay?{urlencode(params)}"

qr_service = UniversalQRService()
