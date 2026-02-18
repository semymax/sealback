import struct
import json
import base64
from pathlib import Path
from src.crypto.constants import MAGIC

from src.crypto.decrypt import decrypt_payload
from src.crypto.encrypt import encrypt_payload
from src.crypto.kdf import generate_salt

class DecryptionError(Exception):
    pass

def write_enc_file(
    input_file: Path,
    output_file: Path,
    password: str
):
    salt = generate_salt()
    data = input_file.read_bytes()
    header = {
        "format_version": 1,
        "cipher": "aes-256-gcm",
        "kdf": "scrypt",
        "kdf_params": {
            "n": 16384,
            "r": 8,
            "p": 1,
            "salt": base64.b64encode(salt).decode()
        },
        "compression": "zstd"
    }
    
    nonce, ciphertext = encrypt_payload(
        data,
        password,
        header
    )
    
    with open(output_file, "wb") as f:
        header_bytes = json.dumps(
            header,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        
        f.write(MAGIC)
        f.write(struct.pack(">I", len(header_bytes)))
        f.write(header_bytes)

        f.write(nonce)
        f.write(ciphertext)

    return output_file

def read_enc_file(
    input_file: Path,
    output_path: Path,
    password: str,
):
    try:
        with open(input_file, "rb") as f:
            magic = f.read(8)
            if magic != MAGIC:
                raise ValueError("Invalid format")

            header_len = struct.unpack(">I", f.read((4)))[0]
            header_bytes = f.read(header_len)
            header = json.loads(header_bytes.decode())

            nonce = f.read(12)
            ciphertext = f.read()
        
        decrypted = decrypt_payload(
            nonce,
            ciphertext,
            password,
            header
        )
    except Exception as e:
        raise DecriptionError(f"Decryption failed (wrong password or corrupted file)") from e

    output_file = output_path / "payload.tar.zst"
    output_file.write_bytes(decrypted)
    
    return output_file
