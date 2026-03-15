"""
app/services/webauthn_service.py

WebAuthn / Passkeys service — registration and authentication flows.
Uses the `webauthn` (py_webauthn) library.

RP_ID is the domain (without protocol). For local dev: "localhost".
RP_NAME is the human-readable app name shown in the browser passkey dialog.
"""

import os
import json
import time
import base64
import secrets

import webauthn
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes

from app.database import SessionLocal
from app.models import User as UserModel, WebAuthnCredential

RP_ID = os.environ.get("WEBAUTHN_RP_ID", "localhost")
RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "Super App")
ORIGIN = os.environ.get("WEBAUTHN_ORIGIN", "http://localhost:8080")

# In-memory challenge store (use Redis in production)
_challenges: dict[str, bytes] = {}


# ── Registration ─────────────────────────────────────────────────────────────

def begin_registration(user_id: str, user_name: str, user_display_name: str) -> dict:
    """
    Generate a WebAuthn credential creation challenge.
    Returns JSON-serialisable options to pass to navigator.credentials.create().
    """
    session = SessionLocal()
    try:
        # Collect existing credential IDs to exclude (don't re-register same authenticator)
        existing = session.query(WebAuthnCredential).filter(
            WebAuthnCredential.user_id == user_id
        ).all()
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
            for c in existing
        ]
    finally:
        session.close()

    options = webauthn.generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=user_id,
        user_name=user_name,
        user_display_name=user_display_name,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=exclude_credentials,
    )

    # Persist challenge for this user
    _challenges[f"reg:{user_id}"] = options.challenge

    return json.loads(webauthn.options_to_json(options))


def complete_registration(
    user_id: str,
    credential_json: dict,
    label: str = "Passkey",
) -> WebAuthnCredential:
    """
    Verify the attestation response and store the new credential.
    Raises ValueError if verification fails.
    """
    challenge = _challenges.pop(f"reg:{user_id}", None)
    if not challenge:
        raise ValueError("No registration challenge found. Session may have expired.")

    verification = webauthn.verify_registration_response(
        credential=credential_json,
        expected_challenge=challenge,
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
    )

    session = SessionLocal()
    try:
        cred = WebAuthnCredential(
            user_id=user_id,
            credential_id=bytes_to_base64url(verification.credential_id),
            public_key=bytes_to_base64url(verification.credential_public_key),
            sign_count=verification.sign_count,
            label=label,
            created_at=time.time(),
        )
        session.add(cred)
        session.commit()
        session.refresh(cred)
        return cred
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Authentication ────────────────────────────────────────────────────────────

def begin_authentication(user_id: str | None = None) -> dict:
    """
    Generate an assertion challenge.
    If user_id is provided, only allows credentials from that user (username-first flow).
    Pass user_id=None for discoverable-credential / usernameless flow.
    """
    allow_credentials = []
    session = SessionLocal()
    try:
        if user_id:
            creds = session.query(WebAuthnCredential).filter(
                WebAuthnCredential.user_id == user_id
            ).all()
            allow_credentials = [
                PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
                for c in creds
            ]
    finally:
        session.close()

    options = webauthn.generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    # Key by session challenge (float RP can have many concurrent auth attempts)
    challenge_key = f"auth:{bytes_to_base64url(options.challenge)}"
    _challenges[challenge_key] = options.challenge

    return json.loads(webauthn.options_to_json(options))


def complete_authentication(assertion_json: dict) -> str:
    """
    Verify the assertion and return the authenticated user_id.
    Updates sign_count to prevent replay attacks.
    Raises ValueError if verification fails.
    """
    # Recover challenge from the assertion's clientDataJSON
    import json as _json
    from base64 import urlsafe_b64decode

    raw_client_data_b64 = assertion_json.get("response", {}).get("clientDataJSON", "")
    # Add padding
    padded = raw_client_data_b64 + "==" * (4 - len(raw_client_data_b64) % 4)
    client_data = _json.loads(urlsafe_b64decode(padded))
    challenge_b64 = client_data.get("challenge", "")
    challenge_key = f"auth:{challenge_b64}"
    challenge = _challenges.pop(challenge_key, None)

    if not challenge:
        raise ValueError("Challenge not found or expired.")

    # Look up the credential by ID
    raw_cred_id = assertion_json.get("id", "")
    session = SessionLocal()
    try:
        cred = session.query(WebAuthnCredential).filter(
            WebAuthnCredential.credential_id == raw_cred_id
        ).first()
        if not cred:
            raise ValueError("Unknown credential. Please register your passkey first.")

        verification = webauthn.verify_authentication_response(
            credential=assertion_json,
            expected_challenge=challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=base64url_to_bytes(cred.public_key),
            credential_current_sign_count=cred.sign_count,
        )

        # Update sign count
        cred.sign_count = verification.new_sign_count
        cred.last_used_at = time.time()
        session.commit()

        return cred.user_id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
