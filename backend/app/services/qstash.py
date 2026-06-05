from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from urllib.parse import quote

import httpx
import jwt

import logging

from app.config import Settings

logger = logging.getLogger(__name__)


def publish_job(settings: Settings, job_id: str) -> None:
    if not settings.qstash_token:
        logger.warning("QStash token is empty, skipping job publish for job_id=%s", job_id)
        return

    callback_url = f"{settings.public_base_url}/internal/jobs/{job_id}/process"
    publish_url = f"{settings.qstash_url}/{callback_url}"
    logger.info("Publishing job %s to QStash. Callback URL: %s", job_id, callback_url)
    logger.info("Full QStash publish URL: %s", publish_url)
    response = httpx.post(
        publish_url,
        headers={
            "Authorization": f"Bearer {settings.qstash_token}",
            "Content-Type": "application/json",
        },
        content=json.dumps({"job_id": job_id}),
        timeout=30.0,
    )
    logger.info("QStash response: status=%s body=%s", response.status_code, response.text[:500])
    response.raise_for_status()


def verify_qstash_signature(raw_body: bytes, signature: str | None, request_url: str, settings: Settings) -> bool:
    if not settings.qstash_current_signing_key:
        logger.info("No QStash signing key configured, skipping signature verification")
        return True
    if not signature:
        logger.warning("No Upstash-Signature header present, rejecting request")
        return False

    logger.info("Verifying QStash signature for URL: %s", request_url)
    result = _verify_with_key(signature, settings.qstash_current_signing_key, raw_body, request_url) or (
        bool(settings.qstash_next_signing_key)
        and _verify_with_key(signature, settings.qstash_next_signing_key, raw_body, request_url)
    )
    if not result:
        logger.warning("QStash signature verification FAILED for URL: %s", request_url)
    else:
        logger.info("QStash signature verification passed")
    return result


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
        logger.warning("QStash sub claim mismatch: token_sub=%s vs request_url=%s", claims.get('sub'), callback_url)
        return False

    body_hash = hashlib.sha256(raw_body).digest()
    encoded_body = base64.urlsafe_b64encode(body_hash).decode("utf-8").rstrip("=")
    return claims.get("body") == encoded_body
