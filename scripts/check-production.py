#!/usr/bin/env python3
"""Read-only deployment probe. No secrets or clinical data required."""
import argparse,sys
from urllib.parse import urlsplit
import httpx
p=argparse.ArgumentParser();p.add_argument('origin');a=p.parse_args()
url=urlsplit(a.origin)
if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('','/'):
    p.error('Use an HTTPS origin without credentials/path/query')
try:
    with httpx.Client(timeout=20,follow_redirects=False) as c:
        config=c.get(a.origin.rstrip('/')+'/api/auth/config');ready=c.get(a.origin.rstrip('/')+'/api/health/ready')
        if config.status_code!=200 or config.json().get('mode')!='accounts':raise ValueError('Individual staff mode not active')
        if ready.status_code!=200 or ready.json().get('hosting_mode')!='production' or not all(ready.json().get('checks',{}).get(key) is True for key in ('database','schema','administrator','least_privilege')):raise ValueError('Production readiness checks did not pass')
        print('Production hosting checks PASS. Clinical readiness remains '+str(ready.json().get('clinical_ready'))+'.')
except ValueError as error:
    print(str(error),file=sys.stderr);raise SystemExit(2)
except Exception:
    print('Deployment could not be verified. Check network, TLS and hosting status.',file=sys.stderr);raise SystemExit(2)
