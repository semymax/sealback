def create_header():
    return {
        "format_version": 1,
        "cipher": "aes-256-gcm",
        "kdf": "scrypt",
        "kdf_params": {
            "n": 16384,
            "r": 8,
            "p": 1,
            "salt": None
        },
        "compression": "zstd"
    }
    