import os
import time
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# Generate a key once and store it in your .env as ENCRYPTION_KEY.
# Local dev should not fail import-time checks when OAuth is not being used.
_key = os.getenv("ENCRYPTION_KEY") or "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
fernet = Fernet(_key.encode())

# In-memory store (replace with a real DB like PostgreSQL in production)
_token_store: dict = {}


def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()


def save_tokens(user_id: str, platform: str, tokens: dict):
    """Encrypt and store tokens for a user."""
    encrypted = {
        "access_token": encrypt_token(tokens["access_token"]),
        "expires_at": tokens.get("expires_at", time.time() + 7200),
        "platform": platform
    }
    if "refresh_token" in tokens:
        encrypted["refresh_token"] = encrypt_token(tokens["refresh_token"])

    _token_store[f"{user_id}:{platform}"] = encrypted
    print(f"[TokenStore] Saved tokens for user={user_id}, platform={platform}")


def get_tokens(user_id: str, platform: str) -> dict | None:
    """Retrieve and decrypt tokens for a user."""
    data = _token_store.get(f"{user_id}:{platform}")
    if not data:
        return None

    result = {
        "access_token": decrypt_token(data["access_token"]),
        "expires_at": data["expires_at"]
    }
    if "refresh_token" in data:
        result["refresh_token"] = decrypt_token(data["refresh_token"])
    return result


def is_token_expired(user_id: str, platform: str) -> bool:
    data = _token_store.get(f"{user_id}:{platform}")
    if not data:
        return True
    return time.time() >= data["expires_at"] - 60  # 60s buffe
