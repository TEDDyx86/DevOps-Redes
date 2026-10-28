"""Password hashing shared with the dependency-free local bootstrap script."""
import hashlib
import hmac
import secrets
import threading


HASH_SLOTS = threading.BoundedSemaphore(2)


def parse_hash(encoded):
    try:
        algorithm, n, r, p, salt, digest = encoded.split("$")
        if (algorithm, n, r, p) != ("scrypt", "131072", "8", "1"):
            return None
        salt, digest = bytes.fromhex(salt), bytes.fromhex(digest)
        return (salt, digest) if len(salt) == 16 and len(digest) == 32 else None
    except (ValueError, AttributeError):
        return None


def derive(password, salt):
    with HASH_SLOTS:
        return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=131072, r=8, p=1,
                              maxmem=256*1024*1024, dklen=32)


def hash_password(password):
    salt = secrets.token_bytes(16)
    return f"scrypt$131072$8$1${salt.hex()}${derive(password, salt).hex()}"


def verify_password(password, encoded):
    parsed = parse_hash(encoded)
    try:
        return bool(parsed and hmac.compare_digest(derive(password, parsed[0]), parsed[1]))
    except UnicodeError:
        return False
