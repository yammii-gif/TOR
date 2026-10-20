#!/usr/bin/env python3
"""Run migrations and catalog seed once, outside Vercel function requests."""
import argparse,os,subprocess,sys
from pathlib import Path
from ops_common import load_env
p=argparse.ArgumentParser();p.add_argument('--env-file');a=p.parse_args()
try:
    load_env(a.env_file);root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
    from backend.app.runtime import validate_configuration,production
    validate_configuration()
    if not production():raise ValueError('Set APP_ENV=production')
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=root/'backend',check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    from backend.app.db import seed
    seed()
    print('Production schema and catalog prepared. Clinical data mode remains synthetic.')
except ValueError as error:
    print(str(error),file=sys.stderr);raise SystemExit(2)
except Exception:
    print('Preparation failed. Check connectivity and migration status without sharing credentials.',file=sys.stderr);raise SystemExit(2)
