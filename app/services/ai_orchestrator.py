import re
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - AI-ORCHESTRATOR - %(levelname)s - %(message)s")
logger = logging.getLogger("AIOrchestrator")

class CognitiveRouter:
    """
    Simulates an On-Device NLP LLM Parser (like Llama 3 Nano).
    In a true production environment with sufficient hardware, this would rely on a local LLM or OpenAI API
    to parse intents via JSON-schema-constrained structured outputs.
    For this architectural prototype, we use targeted heuristic parsing.
    """
    def __init__(self):
        # Basic regex to capture common financial natural language constructs
        # Captures: <action> ... <amount> <currency> ... to <phone/uuid>
        self.transfer_pattern = re.compile(
            r'(?i)(send|pay|transfer)\s+(?:amount\s+of\s+)?\$?(\d+(?:\.\d{1,2})?)\s*(usd|eur|inr|dollars|euros|rupees)?\s+to\s+([+\w]+|-)'
        )
        self.balance_pattern = re.compile(
            r'(?i)(check|show|what is)\s+(my\s+)?(balance|\$|funds|money)'
        )

    def parse_intent(self, natural_language_command: str) -> Dict[str, Any]:
        """
        Tokenizes the natural language string and attempts to deduce the RPC operation payload.
        """
        logger.info(f"Parsing NL Intent: '{natural_language_command}'")
        
        normalized_command = natural_language_command.strip()
        
        # 1. Check for Transfer Intent
        transfer_match = self.transfer_pattern.search(normalized_command)
        if transfer_match:
            action, amount_str, currency_str, target_id = transfer_match.groups()
            
            # Normalize target (remove formatting if phone)
            target = target_id.strip()

            logger.info("Matched TRANSFER intent.")
            return {
                "action": "transfer",
                "confidence": 0.95,
                "payload": {
                    "amount": float(amount_str),
                    "to_target": target, # could be UUID or phone
                    # Currency defaults to USD if not easily parsed locally
                    "currency": currency_str.upper() if currency_str else "USD" 
                }
            }
            
        # 2. Check for Balance Check Intent
        balance_match = self.balance_pattern.search(normalized_command)
        if balance_match:
            logger.info("Matched BALANCE intent.")
            return {
                "action": "check_balance",
                "confidence": 0.90,
                "payload": {}
            }
            
        # Fallback
        logger.warning("Unrecognized intent.")
        return {
            "action": "unknown",
            "confidence": 0.1,
            "payload": {}
        }

# Singleton accessor for gateway
cognitive_router_instance = CognitiveRouter()

def execute_nl_command(command_str: str) -> Dict[str, Any]:
    return cognitive_router_instance.parse_intent(command_str)
