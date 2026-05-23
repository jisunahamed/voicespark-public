import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# Use same key as x_auth if available, or fallback
_key = os.getenv("ENCRYPTION_KEY") or "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
fernet = Fernet(_key.encode())

def encrypt_data(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()
