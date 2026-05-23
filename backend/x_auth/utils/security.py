import os
import base64
import hashlib
import secrets


def generate_code_verifier() -> str:
    """Generate a cryptographically random PKCE code verifier."""
    token = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(token).rstrip(b'=').decode('utf-8')


def generate_code_challenge(verifier: str) -> str:
    """SHA-256 hash the verifier and base64url encode it."""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')


def generate_state() -> str:
    """Generate a random state string for CSRF protection."""
    return secrets.token_urlsafe(32)