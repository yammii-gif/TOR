#!/usr/bin/env python3
"""Manage real staff accounts using an operator connection; passwords via hidden prompt."""
import argparse,getpass,sys
from pathlib import Path
from ops_common import load_env
p=argparse.ArgumentParser();p.add_argument('--env-file');p.add_argument('action',choices=['create','reset-password','disable','enable','set-role']);p.add_argument('--username',required=True);p.add_argument('--role',choices=['physician','pharmacist','admin','researcher'])
a=p.parse_args()
try:
    load_env(a.env_file)
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from backend.app.runtime import production,validate_configuration
    validate_configuration()
    if not production():raise ValueError('Set APP_ENV=production before managing staff')
    from backend.app.db import Session,StaffUser
    from backend.app.identity import create_account,change_account,username
    password=None
    if a.action in ('create','reset-password'):
        password=getpass.getpass('New password (hidden): ')
        if password!=getpass.getpass('Confirm password (hidden): '):raise ValueError('Passwords do not match')
    with Session.begin() as s:
        if a.action=='create':
            if not a.role:raise ValueError('--role is required')
            create_account(s,a.username,password,a.role,'operator-cli')
        else:
            account=s.query(StaffUser).filter_by(username=username(a.username)).first()
            if not account:raise ValueError('Account not found')
            if a.action=='set-role' and not a.role:raise ValueError('--role is required')
            change_account(s,account.id,'operator-cli',role=a.role if a.action=='set-role' else None,
                enabled=False if a.action=='disable' else True if a.action=='enable' else None,password=password)
    print('Staff operation completed. No password or session token was logged.')
except ValueError as error:
    print(str(error),file=sys.stderr);raise SystemExit(2)
except Exception:
    print('Staff operation failed. Check database connectivity and migrations; credentials were not logged.',file=sys.stderr);raise SystemExit(2)
