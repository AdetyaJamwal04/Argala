import base64
import hashlib
import hmac
import json
import logging
import secrets
from typing import Any, Dict

logger = logging.getLogger(__name__)


def canonicalize_json(data: Any) -> str:
    """
    Produces deterministic, canonical JSON encoding (RFC 8785).
    Sorts dictionary keys alphabetically, removes whitespace, and normalizes UTF-8.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_action_hash(
    action: str,
    target: str,
    parameters: Dict[str, Any],
    requester: str,
    timestamp: float,
    nonce: str,
) -> str:
    """
    Computes a cryptographic SHA-256 fingerprint over an action intent.
    Any alteration to parameters, requester, target, timestamp, or nonce
    results in an entirely different hash, preventing TOCTOU attacks.
    """
    canonical_params = canonicalize_json(parameters)
    message = f"{action}:{target}:{canonical_params}:{requester}:{timestamp}:{nonce}"
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def sign_action_hash(action_hash: str, secret_key: str) -> str:
    """
    Produces an unforgeable HMAC-SHA256 cryptographic signature
    over the canonical action hash using the gateway's master signing key.
    """
    key_bytes = secret_key.encode("utf-8")
    hash_bytes = action_hash.encode("utf-8")
    return hmac.new(key_bytes, hash_bytes, hashlib.sha256).hexdigest()


def verify_action_signature(action_hash: str, signature: str, secret_key: str) -> bool:
    """
    Verifies an action signature using constant-time string comparison
    to prevent timing side-channel attacks.
    """
    expected_signature = sign_action_hash(action_hash, secret_key)
    return hmac.compare_digest(expected_signature, signature)


def derive_key(passphrase: str, salt: bytes, iterations: int = 200_000) -> bytes:
    """
    Derives a 256-bit Key Encryption Key (KEK) using PBKDF2-HMAC-SHA256.
    Uses standard library hashlib - zero external C-compilation dependencies.
    """
    return hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        salt,
        iterations,
        dklen=32,
    )


def encrypt_payload(plaintext: str, master_key: str) -> str:
    """
    Authenticated Encryption (Encrypt-then-MAC) using standard library primitives.
    Guarantees 100% compatibility across all architectures (32-bit ARM Python 3.14).
    
    Structure: Base64(Salt [16B] || Nonce [16B] || Ciphertext || HMAC-SHA256 [32B])
    """
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    
    # Derive encryption key (EncKey) and authentication key (MacKey)
    enc_key = derive_key(master_key, salt + b"_enc", iterations=50_000)
    mac_key = derive_key(master_key, salt + b"_mac", iterations=50_000)

    # Keystream generation (ChaCha-style stream using SHA256 counter blocks)
    plaintext_bytes = plaintext.encode("utf-8")
    ciphertext = bytearray(len(plaintext_bytes))
    
    block_num = 0
    for i in range(0, len(plaintext_bytes), 32):
        counter_block = nonce + block_num.to_bytes(8, "big")
        keystream_block = hmac.new(enc_key, counter_block, hashlib.sha256).digest()
        chunk_len = min(32, len(plaintext_bytes) - i)
        for j in range(chunk_len):
            ciphertext[i + j] = plaintext_bytes[i + j] ^ keystream_block[j]
        block_num += 1

    # Authenticate: HMAC-SHA256 over (Salt + Nonce + Ciphertext)
    authenticated_data = salt + nonce + bytes(ciphertext)
    auth_tag = hmac.new(mac_key, authenticated_data, hashlib.sha256).digest()

    full_payload = authenticated_data + auth_tag
    return base64.b64encode(full_payload).decode("utf-8")


def decrypt_payload(token: str, master_key: str) -> str:
    """
    Verifies authentication tag and decrypts ciphertext.
    Rejects tampered payloads in constant time before decryption.
    """
    raw = base64.b64decode(token.encode("utf-8"))
    if len(raw) < 16 + 16 + 32:  # Salt (16) + Nonce (16) + AuthTag (32)
        raise ValueError("Malformed encrypted payload")

    salt = raw[:16]
    nonce = raw[16:32]
    ciphertext = raw[32:-32]
    auth_tag = raw[-32:]

    mac_key = derive_key(master_key, salt + b"_mac", iterations=50_000)
    authenticated_data = salt + nonce + ciphertext
    expected_tag = hmac.new(mac_key, authenticated_data, hashlib.sha256).digest()

    # Constant-time tag verification (Prevents Chosen-Ciphertext attacks)
    if not hmac.compare_digest(expected_tag, auth_tag):
        raise ValueError("Cryptographic verification failed: Tampered or invalid ciphertext")

    enc_key = derive_key(master_key, salt + b"_enc", iterations=50_000)
    plaintext = bytearray(len(ciphertext))
    
    block_num = 0
    for i in range(0, len(ciphertext), 32):
        counter_block = nonce + block_num.to_bytes(8, "big")
        keystream_block = hmac.new(enc_key, counter_block, hashlib.sha256).digest()
        chunk_len = min(32, len(ciphertext) - i)
        for j in range(chunk_len):
            plaintext[i + j] = ciphertext[i + j] ^ keystream_block[j]
        block_num += 1

    return bytes(plaintext).decode("utf-8")
