from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from urllib.parse import quote

import httpx
import jwt

from app.config import Settings


def publish_job(settings: Settings, job_id: str) -> None:
    if not settings.qstash_token:
        return

    callback_url = f"{settings.public_base_url}/internal/jobs/{job_id}/process"
    response = httpx.post(
        f"{settings.qstash_url}/{quote(callback_url, safe='')}",
        headers={
            "Authorization": f"Bearer {settings.qstash_token}",
            "Content-Type": "application/json",
        },
        content=json.dumps({"job_id": job_id}),
        timeout=30.0,
    )
    response.raise_for_status()


def verify_qstash_signature(raw_body: bytes, signature: str | None, request_url: str, settings: Settings) -> bool:
    if not settings.qstash_current_signing_key:
        return True
    if not signature:
        return False

    return _verify_with_key(signature, settings.qstash_current_signing_key, raw_body, request_url) or (
        bool(settings.qstash_next_signing_key)
        and _verify_with_key(signature, settings.qstash_next_signing_key, raw_body, request_url)
    )


def _verify_with_key(token: str, signing_key: str, raw_body: bytes, callback_url: str) -> bool:
    pieces = token.split(".")
    if len(pieces) != 3:
        return False

    header, payload, received_signature = pieces
    message = f"{header}.{payload}"
    generated_signature = base64.urlsafe_b64encode(
        hmac.new(signing_key.encode("utf-8"), message.encode("utf-8"), digestmod=hashlib.sha256).digest()
    ).decode("utf-8").rstrip("=")

    if not hmac.compare_digest(generated_signature, received_signature):
        return False

    claims = jwt.decode(token, options={"verify_signature": False})
    now = int(time.time())
    if claims.get("iss") != "Upstash":
        return False
    if claims.get("nbf", 0) > now or claims.get("exp", 0) < now:
        return False
    if claims.get("sub", "").rstrip("/") != callback_url.rstrip("/"):
        return False

    body_hash = hashlib.sha256(raw_body).digest()
    encoded_body = base64.urlsafe_b64encode(body_hash).decode("utf-8").rstrip("=")
    return claims.get("body") == encoded_body
