#!/usr/bin/env python3
"""Encrypted PostgreSQL custom backups. Never write plaintext dumps to disk."""
import argparse,hashlib,os,shutil,subprocess,sys
from pathlib import Path
from ops_common import load_env,private_write
p=argparse.ArgumentParser();p.add_argument('--env-file');p.add_argument('action',choices=['keygen','backup','restore']);p.add_argument('--file',type=Path,required=True);p.add_argument('--identity',type=Path);p.add_argument('--recipient');p.add_argument('--confirm-database');a=p.parse_args()
try:
    load_env(a.env_file)
    import pyrage
    if a.action=='keygen':
        identity=pyrage.x25519.Identity.generate()
        private_write(a.file,(str(identity)+'\n').encode())
        print('Store the private identity offline. Public backup recipient: '+str(identity.to_public()))
        raise SystemExit(0)
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from backend.app.runtime import validate_configuration,production
    validate_configuration()
    if not production():raise ValueError('Set APP_ENV=production')
    from backend.app.db import engine
    url=engine.url;env=dict(os.environ,PGHOST=url.host,PGPORT=str(url.port or 5432),PGDATABASE=url.database,
        PGUSER=url.username,PGPASSWORD=url.password,PGSSLMODE='verify-full')
    for key in ('sslrootcert','sslcert','sslkey','channel_binding'):
        if key in url.query:env['PG'+key.upper()]=url.query[key]
    if 'PGSSLROOTCERT' not in env:
        import ssl
        env['PGSSLROOTCERT']=ssl.get_default_verify_paths().cafile
    if a.action=='backup':
        if not a.recipient:raise ValueError('--recipient is required (public age recipient, not private key)')
        binary=shutil.which(os.getenv('PG_DUMP_BIN','pg_dump'))
        if not binary:raise ValueError('Install a PostgreSQL client version matching the server (pg_dump)')
        dump=subprocess.run([binary,'--format=custom','--no-owner','--no-acl'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
        encrypted=pyrage.encrypt(dump,[pyrage.x25519.Recipient.from_str(a.recipient)])
        private_write(a.file,encrypted)
        private_write(str(a.file)+'.sha256',(hashlib.sha256(encrypted).hexdigest()+'\n').encode())
        print('Encrypted backup created. Plaintext was kept in operator memory only; verify a restore to a separate empty database.')
    else:
        if a.confirm_database!=url.database:raise ValueError('--confirm-database must match the separate restore target')
        if not a.identity:raise ValueError('--identity is required')
        if os.name!='nt' and a.identity.stat().st_mode&0o077:raise ValueError('Private identity must have mode600')
        expected=Path(str(a.file)+'.sha256').read_text().strip();encrypted=a.file.read_bytes()
        if hashlib.sha256(encrypted).hexdigest()!=expected:raise ValueError('Backup checksum mismatch')
        # Decrypt/authenticate fully before passing any plaintext into PostgreSQL.
        plaintext=pyrage.decrypt(encrypted,[pyrage.x25519.Identity.from_str(a.identity.read_text().strip())])
        from sqlalchemy import text
        with engine.connect() as c:
            count=c.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")).scalar_one()
            if count:raise ValueError('Restore target is not empty; refusing to modify an existing database')
        binary=shutil.which(os.getenv('PG_RESTORE_BIN','pg_restore'))
        if not binary:raise ValueError('Install the PostgreSQL client (pg_restore)')
        subprocess.run([binary,'--exit-on-error','--single-transaction','--no-owner','--no-acl','--dbname',url.database],input=plaintext,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
        print('Restore completed in the explicitly confirmed empty database. Validate schema, catalog, accounts and audit before any cutover.')
except ValueError as error:
    print(str(error),file=sys.stderr);raise SystemExit(2)
except Exception:
    print('Database operation failed. No credentials or dump contents were logged. Check client version, connectivity and key.',file=sys.stderr);raise SystemExit(2)
