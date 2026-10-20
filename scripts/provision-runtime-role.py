#!/usr/bin/env python3
"""Grant a non-owner PostgreSQL runtime role and write its URL only to a private file."""
import argparse,getpass,sys
from pathlib import Path
from ops_common import load_env,private_write
p=argparse.ArgumentParser();p.add_argument('--env-file');p.add_argument('--role',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--runtime-host');a=p.parse_args()
try:
    load_env(a.env_file);sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from backend.app.runtime import production,validate_configuration
    validate_configuration()
    if not production():raise ValueError('Set APP_ENV=production')
    from backend.app.db import engine
    from psycopg import sql
    if a.output.exists():raise ValueError('Output file already exists; refusing to overwrite')
    password=getpass.getpass('Runtime database password (hidden): ')
    if len(password)<24 or password!=getpass.getpass('Confirm password (hidden): '):raise ValueError('Use a matching password with at least24 characters')
    if a.role==engine.url.username:raise ValueError('Runtime role must differ from migration owner')
    connection=engine.raw_connection()
    try:
        with connection.cursor() as c:
            c.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD {}').format(sql.Identifier(a.role),sql.Literal(password)))
            c.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(engine.url.database),sql.Identifier(a.role)))
            c.execute(sql.SQL('REVOKE CREATE ON SCHEMA public FROM PUBLIC'))
            c.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(a.role)))
            c.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(a.role)))
            c.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {}').format(sql.Identifier(a.role)))
            c.execute(sql.SQL('REVOKE UPDATE,DELETE,TRUNCATE ON TABLE audit FROM {}').format(sql.Identifier(a.role)))
            c.execute(sql.SQL('REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON TABLE alembic_version FROM {}').format(sql.Identifier(a.role)))
        connection.commit()
    finally:connection.close()
    runtime_url=engine.url.set(username=a.role,password=password,host=a.runtime_host or engine.url.host).render_as_string(hide_password=False)
    private_write(a.output,('DATABASE_URL='+runtime_url+'\n').encode())
    print('Runtime role created. Connection URL written only to the requested mode600 file; keep it private.')
except ValueError as error:
    print(str(error),file=sys.stderr);raise SystemExit(2)
except Exception:
    print('Provisioning failed. Check provider role permissions and existing role names; credentials were not logged.',file=sys.stderr);raise SystemExit(2)
