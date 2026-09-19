"""Crypto primitives: canonical JSON, SHA-256, base58btc, did:key Ed25519 sign/verify.

Everything signed/hashed in EvidenceGate goes through canonical_json() first —
deterministic serialization is what makes hashes verifiable offline (Kessa-style).
"""

import hashlib
import json
from typing import Any

B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
# multicodec varint prefix for ed25519-pub
ED25519_MULTICODEC = b"\xed\x01"


def canonical_json(obj: Any) -> bytes:
    """RFC 8785-style deterministic serialization: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def b58encode(raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = B58_ALPHABET[r] + out
    pad = len(raw) - len(raw.lstrip(b"\x00"))
    return "1" * pad + (out or "")


def b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + B58_ALPHABET.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + raw


def did_from_pubkey(pubkey: bytes) -> str:
    """did:key for an Ed25519 public key: did:key:z<base58btc(multicodec||pk)>."""
    return "did:key:z" + b58encode(ED25519_MULTICODEC + pubkey)


def pubkey_from_did(did: str) -> bytes:
    if not did.startswith("did:key:z"):
        raise ValueError(f"not a did:key ed25519 identifier: {did}")
    raw = b58decode(did[len("did:key:z"):])
    if not raw.startswith(ED25519_MULTICODEC) or len(raw) != 34:
        raise ValueError("invalid ed25519 multicodec payload")
    return raw[2:]


def generate_keypair() -> tuple[str, bytes, bytes]:
    """Returns (did, secret_key_bytes, public_key_bytes). Requires pynacl."""
    from nacl.signing import SigningKey

    sk = SigningKey.generate()
    pk = bytes(sk.verify_key)
    return did_from_pubkey(pk), bytes(sk), pk


def sign(secret_key: bytes, message: bytes) -> str:
    from nacl.signing import SigningKey

    sig = SigningKey(secret_key).sign(message).signature
    return b58encode(sig)


def verify(did: str, message: bytes, signature_b58: str) -> bool:
    from nacl.signing import VerifyKey

    try:
        VerifyKey(pubkey_from_did(did)).verify(message, b58decode(signature_b58))
        return True
    except Exception:
        return False


def hash_obj(obj: Any) -> str:
    """SHA-256 of canonical JSON — the content-addressing primitive used everywhere."""
    return sha256(canonical_json(obj))
