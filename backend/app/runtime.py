"""Fail closed for production hosting. Clinical recommendations remain disabled."""
import os
from urllib.parse import urlsplit
from sqlalchemy.engine import make_url


def production():return os.getenv('APP_ENV','development')=='production'


def validate_configuration():
    if os.getenv('APP_ENV','development') not in ('development','test','production'):raise ValueError('APP_ENV must be development, test or production')
    if not production():return
    raw=os.getenv('DATABASE_URL','')
    try:url=make_url(raw.replace('postgres://','postgresql://',1))
    except Exception:raise ValueError('Production requires a valid PostgreSQL DATABASE_URL') from None
    if url.get_backend_name()!='postgresql' or not url.host or not url.username or not url.password:
        raise ValueError('Production requires authenticated PostgreSQL; SQLite fallback is disabled')
    if url.query.get('sslmode')!='verify-full':
        raise ValueError('Production DATABASE_URL requires sslmode=verify-full')
    origin=urlsplit(os.getenv('FRONTEND_ORIGIN',''))
    if origin.scheme!='https' or not origin.hostname or origin.username or origin.password or origin.path not in ('','/') or origin.query or origin.fragment:
        raise ValueError('Production FRONTEND_ORIGIN must be the exact HTTPS website origin')
    if os.getenv('COOKIE_SECURE')!='true':raise ValueError('Production requires COOKIE_SECURE=true')
    if len(os.getenv('SESSION_SECRET',''))<32:raise ValueError('Production requires SESSION_SECRET of at least32 characters')
    if os.getenv('CLINICAL_DATA_MODE','synthetic')!='synthetic':
        raise ValueError('Real-patient mode is not implemented or institutionally approved')


# Keep synchronized with migrations; a regression test checks the Alembic head.
def expected_schema():return '007'
