from hashlib import scrypt
from secrets import token_bytes

def derive_key(
    password: str,
    salt: bytes,
    *,
    n: int = 16384,
    r: int = 8,
    p: int = 1,
    length: int = 32
) -> bytes:
    return scrypt(
        password=password.encode(),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=length
    )
    
def generate_salt(size: int = 16) -> bytes:
    return token_bytes(size)
