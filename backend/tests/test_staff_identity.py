import os
from datetime import datetime,timezone,timedelta
import pytest
from fastapi.testclient import TestClient
from test_safety import db
from app.main import app,sessions
from app.db import Session,StaffUser,StaffSession,AuthAttempt
from app.identity import create_account,change_account,hash_password,check_password
from app.runtime import validate_configuration

PASSWORD='synthetic-test-password-12!'
ORIGIN='https://clinical.example.test'

@pytest.fixture
def staff(monkeypatch):
    monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('SESSION_SECRET','synthetic-runtime-key-at-least32-characters')
    monkeypatch.setenv('FRONTEND_ORIGIN',ORIGIN);monkeypatch.setenv('COOKIE_SECURE','true')
    with Session.begin() as s:
        create_account(s,'staff-admin',PASSWORD,'admin','test-operator')
        create_account(s,'staff-doctor',PASSWORD,'physician','test-operator')
    return TestClient(app,base_url=ORIGIN)


def login(c,name='staff-doctor',password=PASSWORD,**extra):
    return c.post('/auth/login',json={'username':name,'password':password,**extra},headers={'Origin':ORIGIN})


def csrf(c):return {'Origin':ORIGIN,'X-CSRF-Token':c.cookies.get('renal_csrf')}


def test_hashes_salted_and_no_plaintext():
    a=hash_password(PASSWORD);b=hash_password(PASSWORD)
    assert a!=b and PASSWORD not in a
    assert check_password(PASSWORD,a) and not check_password('wrong',a)


def test_server_decides_role_sessions_survive_workers_and_logout_revokes(staff):
    c=staff;r=login(c,role='admin');assert r.status_code==200 and r.json()['role']=='physician'
    token=c.cookies.get('session');sessions.clear()
    other=TestClient(app,base_url=ORIGIN);other.cookies.set('session',token)
    assert other.get('/auth/me').json()['role']=='physician'
    with Session() as s:
        assert s.query(StaffSession).count()==1
        assert not any(row.token_hash==token for row in s.query(StaffSession))
    assert c.post('/auth/logout',headers=csrf(c)).status_code==200
    assert other.get('/auth/me').status_code==401


def test_csrf_and_origin_are_required_for_mutations(staff):
    c=staff;assert login(c).status_code==200
    assert c.post('/prescriptions',json={'drug':'any','proposal':'fixture','decision':'MODIFY'}).status_code==403
    headers=csrf(c)|{'Origin':'https://evil.example'}
    assert c.post('/auth/logout',headers=headers).status_code==403
    assert c.post('/auth/login',json={'username':'staff-doctor','password':PASSWORD}).status_code==403


def test_only_admin_can_manage_accounts_and_disable_revokes(staff):
    c=staff;login(c)
    assert c.post('/admin/users',headers=csrf(c),json={'username':'new-staff','password':PASSWORD,'role':'admin'}).status_code==403
    admin=TestClient(app,base_url=ORIGIN);assert login(admin,'staff-admin').status_code==200
    row=next(a for a in admin.get('/admin/users').json() if a['username']=='staff-doctor')
    assert admin.post(f"/admin/users/{row['id']}",headers=csrf(admin),json={'enabled':False}).status_code==200
    assert c.get('/auth/me').status_code==401
    assert login(c).status_code==401
    assert 'password_hash' not in admin.get('/admin/users').text


def test_password_change_revokes_sessions_and_last_admin_protected(staff):
    c=staff;login(c)
    with Session.begin() as s:
        doctor=s.query(StaffUser).filter_by(username='staff-doctor').one()
        change_account(s,doctor.id,'test-admin',password='synthetic-new-password-12!')
    assert c.get('/auth/me').status_code==401
    assert login(c).status_code==401
    admin=TestClient(app,base_url=ORIGIN);login(admin,'staff-admin')
    row=admin.get('/admin/users').json()[0]
    assert admin.post(f"/admin/users/{row['id']}",headers=csrf(admin),json={'enabled':False}).status_code==409


def test_throttle_persists_across_clients_and_expires(staff):
    for _ in range(5):assert login(staff,password='wrong-password').status_code==401
    assert login(TestClient(app,base_url=ORIGIN)).status_code==429
    with Session.begin() as s:
        bucket=s.query(AuthAttempt).one();bucket.window_started=datetime.now(timezone.utc)-timedelta(minutes=16)
    assert login(staff).status_code==200


def test_expired_session_not_accepted(staff):
    login(staff)
    with Session.begin() as s:s.query(StaffSession).one().expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    assert staff.get('/auth/me').status_code==401


def test_production_rejects_demo_password_and_redacts_validation_inputs(staff):
    assert staff.post('/auth/login',json={'role':'admin','password':'test-password-only'},headers={'Origin':ORIGIN}).status_code==401
    secret='s'*257
    r=staff.post('/auth/login',json={'username':'staff-doctor','password':secret},headers={'Origin':ORIGIN})
    assert r.status_code==422 and secret not in r.text and 'input' not in r.json()['detail'][0]


@pytest.mark.parametrize('key,value',[
    ('DATABASE_URL','sqlite:////tmp/unsafe.db'),('DATABASE_URL','postgresql://user:password@db.example.test/renal?sslmode=require'),
    ('FRONTEND_ORIGIN','http://clinical.example.test'),('COOKIE_SECURE','false'),('SESSION_SECRET','short'),('CLINICAL_DATA_MODE','real'),
])
def test_production_config_fails_closed(monkeypatch,key,value):
    for k,v in {'APP_ENV':'production','DATABASE_URL':'postgresql://user:password@db.example.test/renal?sslmode=verify-full',
                'FRONTEND_ORIGIN':ORIGIN,'COOKIE_SECURE':'true','SESSION_SECRET':'synthetic-key-at-least32-characters-long','CLINICAL_DATA_MODE':'synthetic'}.items():monkeypatch.setenv(k,v)
    monkeypatch.setenv(key,value)
    with pytest.raises(ValueError):validate_configuration()


def test_prescription_idempotency_and_payload_mismatch(staff):
    from test_safety import METFORMIN_PRODUCT
    from app.db import Prescription
    login(staff)
    body={'drug':METFORMIN_PRODUCT,'proposal':'synthetic manual physician decision','decision':'MODIFY'}
    assert staff.post('/prescriptions',headers=csrf(staff),json=body).status_code==422
    headers=csrf(staff)|{'Idempotency-Key':'synthetic-request-1'}
    first=staff.post('/prescriptions',headers=headers,json=body)
    second=staff.post('/prescriptions',headers=headers,json=body)
    assert first.status_code==second.status_code==200
    assert first.json()['id']==second.json()['id'] and second.json()['replayed']
    assert staff.post('/prescriptions',headers=headers,json=body|{'proposal':'different proposal'}).status_code==409
    with Session() as s:assert s.query(Prescription).count()==1


def test_readiness_revision_matches_migration_head():
    from pathlib import Path
    from alembic.script import ScriptDirectory
    from app.runtime import expected_schema
    assert expected_schema()==ScriptDirectory(str(Path(__file__).parents[1]/'alembic')).get_current_head()
