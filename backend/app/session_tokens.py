"""Signed demo sessions for functions that do not share process memory."""
import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone


def enabled():
    return os.getenv('SERVERLESS_DEMO') == 'true'


def _key():
    value = os.getenv('SESSION_SECRET', '')
    if len(value) < 32:
        raise ValueError('SESSION_SECRET must contain at least 32 characters')
    return value.encode()


def issue(entry):
    payload = json.dumps({
        'name': entry['name'], 'role': entry['role'],
        'exp': int(entry['expires'].timestamp()), 'nonce': secrets.token_urlsafe(16),
    }, separators=(',', ':')).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip('=')
    signature = hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()
    return body + '.' + signature


def verify(token):
    try:
        if len(token) > 2048:
            return None
        body, signature = token.split('.')
        expected = hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
        if data['role'] not in ['physician', 'pharmacist', 'admin', 'researcher']:
            return None
        expires = datetime.fromtimestamp(data['exp'], timezone.utc)
        if expires <= datetime.now(timezone.utc):
            return None
        return {'name': data['name'], 'role': data['role'], 'expires': expires}
    except (ValueError, KeyError, TypeError, OverflowError):
        return None
