"""Operator helpers: never execute env files or print credential values."""
import os,re
from pathlib import Path


def load_env(path):
    if not path:return
    path=Path(path)
    if os.name!='nt' and path.stat().st_mode&0o077:raise ValueError('Environment file must have mode600')
    for line in path.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        key,separator,value=line.partition('=')
        if not separator or not re.fullmatch('[A-Z_][A-Z0-9_]*',key):raise ValueError('Invalid environment file')
        if len(value)>=2 and value[0]==value[-1] and value[0] in ('"',"'"):value=value[1:-1]
        os.environ.setdefault(key,value)


def private_write(path,data):
    path=Path(path)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write(data)
