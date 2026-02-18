import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from secrets import token_bytes
from src.crypto.kdf import derive_key, generate_salt

def encrypt_payload(
    data: bytes,
    password: str,
    header: dict,
) -> tuple[bytes, bytes]:
    salt = base64.b64decode(header["kdf_params"]["salt"])
    key = derive_key(
        password,
        salt,
        n = header["kdf_params"]["n"],
        r = header["kdf_params"]["r"],
        p = header["kdf_params"]["p"],
    )
    
    aesgcm = AESGCM(key)
    nonce = token_bytes(12)
    
    header_bytes = json.dumps(
        header,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    encrypted = aesgcm.encrypt(nonce, data, header_bytes)

    return nonce, encrypted