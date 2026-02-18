import base64
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.crypto.kdf import derive_key

def decrypt_payload(
    nonce: bytes,
    data: bytes,
    password: str,
    header: dict,
) -> bytes:
    salt = base64.b64decode(header["kdf_params"]["salt"])
    key = derive_key(
        password,
        salt,
        n = header["kdf_params"]["n"],
        r = header["kdf_params"]["r"],
        p = header["kdf_params"]["p"],
    )

    header_bytes = json.dumps(
        header,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    aesgcm = AESGCM(key)
    
    return aesgcm.decrypt(nonce, data, header_bytes)
