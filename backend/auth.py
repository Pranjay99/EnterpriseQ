"""
auth.py — Supabase JWT verification for API routes.

Every /api route requires a valid Supabase access token
(Authorization: Bearer <jwt>), verified in one of two ways:

  1. SUPABASE_JWT_SECRET set  → HS256 verification (legacy JWT secret,
     found in Supabase Dashboard → Settings → API → JWT Secret).
  2. Only SUPABASE_URL set    → asymmetric verification via the project's
     JWKS endpoint (new Supabase projects use ES256/RS256 signing keys).

If neither variable is set, auth is DISABLED: every request runs as a
shared "dev-user". This keeps local development working before the
Supabase project is configured — never deploy in this state.
"""

import logging
import os

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "").strip()
_SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")

_AUTH_ENABLED = bool(_JWT_SECRET or _SUPABASE_URL)
if not _AUTH_ENABLED:
    logger.warning(
        "AUTH DISABLED — set SUPABASE_JWT_SECRET (or SUPABASE_URL) in .env "
        "to require login. All requests run as 'dev-user'."
    )

# JWKS client is lazy so startup never blocks on a network call.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            f"{_SUPABASE_URL}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
        )
    return _jwks_client


def _decode_token(token: str) -> dict:
    if _JWT_SECRET:
        return jwt.decode(
            token,
            _JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
    )


_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency — returns {"id": <supabase user id>, "email": <email>}.
    Raises 401 when auth is enabled and the token is missing/invalid.
    """
    if not _AUTH_ENABLED:
        return {"id": "dev-user", "email": "dev@local"}

    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated. Please sign in.")

    try:
        payload = _decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    return {"id": payload["sub"], "email": payload.get("email", "")}
