"""
gateway/utils.py

PII (Personally Identifiable Information) masking utilities for regional compliance.
Authorized admins in the same region can see full data.
Cross-region admins or generic reports should see masked data.
"""

import re

def mask_email(email: str) -> str:
    """Mask email: user@example.com -> u***@example.com"""
    if not email or "@" not in email:
        return email
    user, domain = email.split("@", 1)
    if len(user) <= 1:
        return f"*@{domain}"
    return f"{user[0]}***@{domain}"

def mask_phone(phone: str) -> str:
    """Mask phone: +1234567890 -> +123****890"""
    if not phone or len(phone) < 7:
        return "****"
    return f"{phone[:4]}****{phone[-3:]}"

def mask_name(name: str) -> str:
    """Mask name: John Doe -> J*** D***"""
    parts = name.split()
    masked_parts = []
    for p in parts:
        if len(p) <= 1:
            masked_parts.append("*")
        else:
            masked_parts.append(f"{p[0]}***")
    return " ".join(masked_parts)

def mask_voter_id(voter_id: str) -> str:
    """Mask Voter ID: ABC1234567 -> ABC****567"""
    if not voter_id or len(voter_id) < 6:
        return "****"
    return f"{voter_id[:3]}****{voter_id[-3:]}"

def mask_user_pii(user_dict: dict) -> dict:
    """Recursively mask PII fields in a user dictionary."""
    if "email" in user_dict:
        user_dict["email"] = mask_email(user_dict["email"])
    if "phone_number" in user_dict:
        user_dict["phone_number"] = mask_phone(user_dict["phone_number"])
    if "name" in user_dict:
        user_dict["name"] = mask_name(user_dict["name"])
    if "voter_id" in user_dict:
        user_dict["voter_id"] = mask_voter_id(user_dict["voter_id"])
    return user_dict
