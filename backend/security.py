import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt

ALGORITHM = "HS256"
TOKEN_TYPE = "access"
PBKDF2_ITERATIONS = 600_000
MIN_SECRET_LENGTH = 32


def get_secret_key():
    secret = os.environ.get("JWT_SECRET_KEY", "")
    if len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            "JWT_SECRET_KEY must be set to at least 32 characters."
        )
    return secret


def token_expiry_minutes():
    raw = os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    try:
        minutes = int(raw)
    except (TypeError, ValueError) as error:
        raise RuntimeError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be an integer.") from error
    if minutes < 1 or minutes > 10080:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 10080."
        )
    return minutes


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"
    )


def verify_password(password, encoded):
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(candidate, bytes.fromhex(digest_hex))
    except (AttributeError, TypeError, ValueError):
        return False


def create_access_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "ver": int(user.get("token_version", 0)),
        "type": TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=token_expiry_minutes()),
    }
    return jwt.encode(payload, get_secret_key(), algorithm=ALGORITHM)


def decode_access_token(token):
    try:
        payload = jwt.decode(
            token,
            get_secret_key(),
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError:
        return None

    if payload.get("type") != TOKEN_TYPE:
        return None
    return payload
