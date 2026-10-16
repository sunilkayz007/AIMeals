"""
=========================================================
AIMeals Backend
AdMob SSV Verification Service

Responsibilities:
    - Fetch and cache Google's published AdMob SSV public keys
    - Verify the ECDSA/SHA-256 signature on a rewarded-ad
      server-side-verification (SSV) callback

Dependencies:
    - httpx (async HTTP client, for fetching Google's key JSON)
    - cryptography (ECDSA signature verification)

Notes:
    - Google's documented SSV algorithm: the "content to verify"
      is the raw callback query string, taken from the start up
      to (but not including) the "&signature=" parameter — i.e.
      everything Google appended BEFORE it signed the request.
      The "signature" and "key_id" parameters themselves are
      never part of the signed content.
    - The signature query param is web-safe (URL-safe) base64,
      and decodes to a DER-encoded ECDSA signature over that
      content, using SHA-256 and Google's published P-256
      (prime256v1) public key identified by key_id.
    - Google's key JSON
      (https://www.gstatic.com/admob/reward/verifier-keys.json)
      rotates periodically. Keys are cached in-process, honoring
      the response's Cache-Control max-age when present, with a
      1-hour fallback TTL otherwise. If a key_id isn't found in
      the cache, ONE forced refresh is attempted before giving
      up — covers the case where a key rotated since the last
      fetch.
    - ⚠️ IMPORTANT: this implementation is written directly from
      Google's public SSV documentation but has NOT been tested
      against Google's live infrastructure from this environment.
      Before relying on this in production, verify it against
      Google's own SSV testing tool (AdMob console -> Mediation
      -> your rewarded ad unit -> SSV testing), which sends a
      real signed test callback to your endpoint.

Example usage:
    from app.services.admob_verification import verify_ssv_signature

    is_valid = await verify_ssv_signature(
        raw_query_string=request.url.query,
        signature=signature,
        key_id=key_id,
    )
=========================================================
"""

import base64
import time
from typing import Optional

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

GOOGLE_SSV_KEYS_URL = "https://www.gstatic.com/admob/reward/verifier-keys.json"

# Fallback cache lifetime if Google's response has no usable
# Cache-Control max-age header. Google recommends caching but
# refreshing periodically to pick up key rotation.
_DEFAULT_KEY_CACHE_TTL_SECONDS = 60 * 60  # 1 hour

# In-process cache: {key_id: pem_string}. Simple module-level
# cache is sufficient here — key rotation is infrequent and this
# is a single-process FastAPI app.
_key_cache: dict[str, str] = {}
_key_cache_expires_at: float = 0.0


async def _fetch_google_keys() -> dict[str, str]:
    """
    Fetches Google's current SSV public keys and returns them as
    {key_id: pem_string}. Does NOT itself decide caching — see
    _get_google_keys() for the cache-aware wrapper.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(GOOGLE_SSV_KEYS_URL)
        response.raise_for_status()

    payload = response.json()
    keys_by_id = {
        str(key["keyId"]): key["pem"] for key in payload.get("keys", [])
    }

    ttl = _DEFAULT_KEY_CACHE_TTL_SECONDS
    cache_control = response.headers.get("cache-control", "")
    for directive in cache_control.split(","):
        directive = directive.strip()
        if directive.startswith("max-age="):
            try:
                ttl = max(60, int(directive.split("=", 1)[1]))
            except ValueError:
                pass

    global _key_cache, _key_cache_expires_at
    _key_cache = keys_by_id
    _key_cache_expires_at = time.time() + ttl

    return keys_by_id


async def _get_google_keys(force_refresh: bool = False) -> dict[str, str]:
    """
    Returns the cached key set, refreshing it if expired or if
    force_refresh is True (used when a key_id isn't found in the
    current cache — it may have rotated since the last fetch).
    """
    if force_refresh or not _key_cache or time.time() >= _key_cache_expires_at:
        return await _fetch_google_keys()
    return _key_cache


def _b64url_decode(data: str) -> bytes:
    """
    Decodes a web-safe (URL-safe) base64 string, adding back any
    padding that AdMob's query-param encoding strips.
    """
    padding_needed = (-len(data)) % 4
    return base64.urlsafe_b64decode(data + ("=" * padding_needed))


def _content_to_verify(raw_query_string: str) -> str:
    """
    Extracts the exact substring Google signed: everything in the
    raw query string BEFORE the "signature" parameter. Per
    Google's SSV docs, "signature" and "key_id" are always the
    last two parameters Google appends, in that order, so this
    is simply the query string truncated at "&signature=".

    Raises ValueError if "signature=" isn't found — that means
    the request doesn't actually look like a real AdMob callback
    and should be rejected before ever reaching key verification.
    """
    marker = "signature="
    idx = raw_query_string.find(marker)
    if idx <= 0:
        raise ValueError(
            "Query string does not contain a 'signature=' parameter "
            "in the expected position; not a valid AdMob SSV callback."
        )
    # Strip the trailing "&" that precedes "signature=".
    return raw_query_string[: idx - 1] if raw_query_string[idx - 1] == "&" else raw_query_string[:idx]


async def verify_ssv_signature(
    raw_query_string: str,
    signature: str,
    key_id: str,
) -> bool:
    """
    Verifies an AdMob rewarded-ad SSV callback's signature.

    Args:
        raw_query_string: the RAW, as-received query string of the
            callback request (e.g. request.url.query in FastAPI/
            Starlette) — must be the original string, not a
            re-serialized dict of parsed params, since parameter
            order matters for reconstructing the signed content.
        signature: the "signature" query parameter's value.
        key_id: the "key_id" query parameter's value.

    Returns:
        True if the signature is valid for the given content and
        key, False for any verification failure (unknown key_id
        even after a forced refresh, malformed signature, or a
        signature that doesn't match).
    """
    try:
        content = _content_to_verify(raw_query_string)
    except ValueError:
        return False

    keys = await _get_google_keys()
    pem = keys.get(key_id)

    if pem is None:
        # Key may have rotated since our last fetch — try once more
        # with a forced refresh before giving up.
        keys = await _get_google_keys(force_refresh=True)
        pem = keys.get(key_id)

    if pem is None:
        return False

    try:
        public_key = serialization.load_pem_public_key(pem.encode("utf-8"))
    except ValueError:
        return False

    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        return False

    try:
        signature_bytes = _b64url_decode(signature)
    except Exception:
        return False

    try:
        public_key.verify(
            signature_bytes,
            content.encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except InvalidSignature:
        return False