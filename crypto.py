import hashlib
from cryptography.fernet import Fernet
import config

_f = Fernet(config.FERNET_KEY.encode())

def enc(s: str) -> str:
    return _f.encrypt(s.encode()).decode()

def dec(s: str) -> str:
    return _f.decrypt(s.encode()).decode()

def thash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()
