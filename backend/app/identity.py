"""Database-backed identity. Never trust a role supplied by the login browser."""
import hashlib,hmac,os,re,secrets
from datetime import datetime,timezone,timedelta
from fastapi import HTTPException
from sqlalchemy import case
from .db import Session,StaffUser,StaffSession,AuthAttempt,Audit

ROLES=('physician','pharmacist','admin','researcher')


def username(value):
    value=value.strip().lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{2,63}',value):raise ValueError('Username must contain3–64 Latin letters, digits, dot, underscore or hyphen')
    return value


def hash_password(password):
    if not 12<=len(password)<=256:raise ValueError('Password must contain12–256 characters')
    salt=secrets.token_bytes(16)
    digest=hashlib.scrypt(password.encode(),salt=salt,n=32768,r=8,p=1,dklen=32,maxmem=67108864)
    return f'scrypt$32768$8$1${salt.hex()}${digest.hex()}'


def check_password(password,encoded):
    try:
        algorithm,n,r,p,salt,expected=encoded.split('$')
        if (algorithm,n,r,p)!=('scrypt','32768','8','1') or len(salt)!=32 or len(expected)!=64:return False
        actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=32768,r=8,p=1,dklen=32,maxmem=67108864)
        return secrets.compare_digest(actual,bytes.fromhex(expected))
    except (ValueError,TypeError):return False


DUMMY=hash_password(secrets.token_urlsafe(32))


def digest(value):return hashlib.sha256(value.encode()).hexdigest()


def aware(value):return value.replace(tzinfo=value.tzinfo or timezone.utc)


def origin_check(request):
    if request.headers.get('origin')!=os.getenv('FRONTEND_ORIGIN','').rstrip('/'):
        raise HTTPException(403,'ต้นทางคำขอไม่ถูกต้อง')


def bucket_key(name):return hmac.new(os.environ['SESSION_SECRET'].encode(),name.encode(),hashlib.sha256).hexdigest()


def security_audit(s,name,action,previous,new):
    s.add(Audit(user=name,action=action,previous=previous,new=new,comments=''))


def login(request,response,name,password):
    origin_check(request)
    try:name=username(name or '')
    except ValueError:raise HTTPException(401,'ข้อมูลเข้าสู่ระบบไม่ถูกต้อง')
    now=datetime.now(timezone.utc);bucket=bucket_key(name);cutoff=now-timedelta(minutes=15)
    with Session.begin() as s:
        if s.bind.dialect.name=='postgresql':
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        stmt=insert(AuthAttempt).values(bucket=bucket,attempts=1,window_started=now)
        stmt=stmt.on_conflict_do_update(index_elements=['bucket'],set_={
            'attempts':case((AuthAttempt.window_started<cutoff,1),else_=AuthAttempt.attempts+1),
            'window_started':case((AuthAttempt.window_started<cutoff,now),else_=AuthAttempt.window_started)}).returning(AuthAttempt.attempts)
        attempts=s.execute(stmt).scalar_one()
        account=s.query(StaffUser).filter_by(username=name).first()
        encoded=account.password_hash if account else DUMMY
        account_id=account.id if account else None
    if attempts>5:raise HTTPException(429,'เข้าสู่ระบบไม่สำเร็จหลายครั้ง กรุณารอ15นาที')
    valid=check_password(password,encoded)
    with Session.begin() as s:
        account=s.get(StaffUser,account_id,with_for_update=True) if account_id else None
        if not valid or not account or not account.enabled or account.password_hash!=encoded:
            security_audit(s,account.username if account else 'unknown-account','LOGIN_FAILED','ANONYMOUS','DENIED')
            denied=True
        else:
            denied=False
            token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
            s.add(StaffSession(token_hash=digest(token),user_id=account.id,csrf_hash=digest(csrf),
                               auth_version=account.auth_version,expires_at=now+timedelta(hours=4)))
            s.query(AuthAttempt).filter_by(bucket=bucket).delete()
            security_audit(s,account.username,'LOGIN_STAFF','ANONYMOUS','AUTHENTICATED')
            result={'name':account.username,'role':account.role,'mode':'ACCOUNTS','clinical_data_mode':'SYNTHETIC_DATA'}
    if denied:raise HTTPException(401,'ข้อมูลเข้าสู่ระบบไม่ถูกต้อง')
    response.set_cookie('session',token,httponly=True,secure=True,samesite='strict',max_age=14400)
    response.set_cookie('renal_csrf',csrf,httponly=False,secure=True,samesite='strict',max_age=14400)
    return result


def authenticate(request,token):
    if not token or len(token)>256:raise HTTPException(401,'กรุณาเข้าสู่ระบบ')
    now=datetime.now(timezone.utc)
    with Session() as s:
        session=s.get(StaffSession,digest(token))
        account=s.get(StaffUser,session.user_id) if session else None
        if not session or not account or not account.enabled or aware(session.expires_at)<=now or session.auth_version!=account.auth_version:
            raise HTTPException(401,'กรุณาเข้าสู่ระบบใหม่')
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin_check(request)
            csrf=request.headers.get('x-csrf-token','')
            if not csrf or len(csrf)>256 or not secrets.compare_digest(digest(csrf),session.csrf_hash):raise HTTPException(403,'CSRF token ไม่ถูกต้อง')
        return {'name':account.username,'role':account.role,'expires':aware(session.expires_at),'account_id':account.id}


def logout(request,response,token):
    origin_check(request)
    if token:
        entry=authenticate(request,token)
        with Session.begin() as s:
            s.query(StaffSession).filter_by(token_hash=digest(token)).delete()
            security_audit(s,entry['name'],'LOGOUT_STAFF','AUTHENTICATED','REVOKED')
    response.delete_cookie('session',secure=True,samesite='strict')
    response.delete_cookie('renal_csrf',secure=True,samesite='strict')
    return {'ok':True}


def account_view(account):return {'id':account.id,'username':account.username,'role':account.role,'enabled':account.enabled}


def create_account(s,name,password,role,actor):
    name=username(name)
    if role not in ROLES:raise ValueError('Invalid role')
    if s.query(StaffUser).filter_by(username=name).first():raise ValueError('Username already exists')
    account=StaffUser(username=name,password_hash=hash_password(password),role=role)
    s.add(account);s.flush();security_audit(s,actor,'STAFF_CREATED','NONE',f'{name}:{role}')
    return account_view(account)


def change_account(s,account_id,actor,role=None,enabled=None,password=None):
    admins=s.query(StaffUser).filter_by(role='admin',enabled=True).order_by(StaffUser.id).with_for_update().all()
    account=s.get(StaffUser,account_id,with_for_update=True,populate_existing=True)
    if not account:raise ValueError('Account not found')
    if role is not None and role not in ROLES:raise ValueError('Invalid role')
    if account.role=='admin' and account.enabled and (enabled is False or role is not None and role!='admin'):
        # Serialize admin changes to prevent two administrators removing the last admin concurrently.
        if len(admins)<=1:raise ValueError('Cannot disable or demote the last administrator')
    previous=f'{account.username}:{account.role}:{account.enabled}'
    if role is not None:account.role=role
    if enabled is not None:account.enabled=enabled
    if password is not None:account.password_hash=hash_password(password)
    account.auth_version+=1
    s.query(StaffSession).filter_by(user_id=account.id).delete()
    s.query(AuthAttempt).filter_by(bucket=bucket_key(account.username)).delete()
    security_audit(s,actor,'STAFF_CHANGED',previous,f'{account.username}:{account.role}:{account.enabled}')
    return account_view(account)
