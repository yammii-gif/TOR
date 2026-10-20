"""Vercel function adapter for the existing synthetic FastAPI service."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if os.getenv('APP_ENV')!='production':os.environ['SERVERLESS_DEMO']='true'
from backend.app.runtime import validate_configuration
validate_configuration()
os.environ.setdefault('COOKIE_SECURE', 'true')

from fastapi import FastAPI
from backend.app.db import Base, engine, seed
from backend.app.main import app as clinical_app

# Local /tmp storage is deliberately limited to a disposable synthetic demo.
# A shared database needs normal migrations and institutional deployment review.
if engine.dialect.name == 'sqlite' and os.getenv('APP_ENV')!='production':
    Base.metadata.create_all(engine)
    seed()

app = FastAPI(title='Renal Smart CDSS — serverless synthetic demo')
app.mount('/api', clinical_app)
