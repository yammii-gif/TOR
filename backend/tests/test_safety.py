import os
os.environ['DATABASE_URL']='sqlite:////tmp/renal-smart-test.db'
os.environ['DEMO_PASSWORD']='test-password-only'
from datetime import datetime,timezone,timedelta
import pytest
from fastapi.testclient import TestClient
from app.db import Base,engine,seed,Session,Audit
from app.main import app
from app.clinical import RenalInput,calculate,evaluate
@pytest.fixture(autouse=True)
def db():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine);seed()
def patient(**kw):
    data=dict(age=65,weight_kg=60,sex='male',scr=1.5,collected_at=datetime.now(timezone.utc),verified=True,actual_weight_appropriate=True)
    return RenalInput(**(data|kw))
def client(role):
    c=TestClient(app);assert c.post('/auth/login',json={'role':role,'password':'test-password-only'}).status_code==200;return c
@pytest.mark.parametrize('sex,factor',[('male',1),('female',.85)])
def test_formula(sex,factor):assert calculate(patient(sex=sex))['crcl']==round(75*60/108*factor,2)
def test_units():assert calculate(patient(scr=132.6,unit='µmol/L'))['crcl']==calculate(patient())['crcl']
@pytest.mark.parametrize('hours,status',[(47.99,'SIMULATION'),(48.01,'VERIFICATION_REQUIRED'),(-1,'VERIFICATION_REQUIRED')])
def test_lab_boundary(hours,status):assert calculate(patient(collected_at=datetime.now(timezone.utc)-timedelta(hours=hours)))['status']==status
@pytest.mark.parametrize('kw',[{'stable':False},{'dialysis':None},{'actual_weight_appropriate':False}])
def test_review(kw):assert calculate(patient(**kw))['status']=='CLINICAL_REVIEW_REQUIRED'
def test_missing():
    with pytest.raises(ValueError):RenalInput(age=65)
def test_no_alternative():assert evaluate(patient(),indication=None)['dose'] is None
@pytest.mark.parametrize('scr',[.99,1,1.01,2,10])
def test_no_invented_threshold(scr):assert evaluate(patient(scr=scr),indication='diabetes')['dose'] is None
def test_ocr():
    c=client('physician');p=dict(patient_id='SYN-002',expected_patient_id='SYN-001',confidence=.99,fields={},monitoring=True)
    assert c.post('/agent/capture',json=p).json()['status']=='VERIFICATION_REQUIRED'
    p.update(patient_id='SYN-001',confidence=.5);assert c.post('/agent/capture',json=p).json()['status']=='VERIFICATION_REQUIRED'
def test_workflow():
    doctor=client('physician');pharmacist=client('pharmacist')
    payload=dict(drug='Metformin',proposal='ข้อเสนอจำลอง',decision='OVERRIDE',reason='')
    assert doctor.post('/prescriptions',json=payload).status_code==422
    payload['reason']='ทบทวนโดยแพทย์';r=doctor.post('/prescriptions',json=payload);assert r.status_code==200
    id=r.json()['id']
    assert doctor.post(f'/prescriptions/{id}/review',json={'action':'VERIFIED','comments':'test'}).status_code==403
    assert pharmacist.post(f'/prescriptions/{id}/review',json={'action':'REJECTED','comments':'ข้อมูลไม่เพียงพอ'}).json()['status']=='REJECTED'
    assert len(pharmacist.get('/audit').json())==2
    with Session.begin() as s:
        a=s.query(Audit).first();a.comments='tamper'
        with pytest.raises(ValueError):s.flush()
def test_rule_activation_and_version():
    c=client('pharmacist')
    a=c.post('/rules/1/draft').json();b=c.post('/rules/1/draft').json();assert b['version']==a['version']+1
    assert c.post(f"/rules/{a['id']}/transition",json={'action':'ACTIVE','comments':'bad'}).status_code==409
    assert client('physician').post('/rules/1/draft').status_code==403
def test_auth():assert TestClient(app).get('/patients').status_code==401

def test_snapshot_and_repeated_review():
    c=client('physician')
    r=c.post('/prescriptions',json={'drug':'Metformin','proposal':'synthetic only','decision':'MODIFY'}).json()
    p=client('pharmacist');record=p.get('/prescriptions').json()[0]
    assert record['source_snapshot']['id']=='SYN-001'
    assert 'calculation' in record['source_snapshot']
    payload={'action':'CLARIFICATION','comments':'ขอข้อมูลเพิ่ม'}
    assert p.post(f"/prescriptions/{r['id']}/review",json=payload).status_code==200
    assert p.post(f"/prescriptions/{r['id']}/review",json=payload).status_code==409
    assert p.get('/audit').json()[0]['record_id']==r['id']

def test_no_unvalidated_acceptance():
    c=client('physician')
    assert c.post('/prescriptions',json={'drug':'Metformin','proposal':'demo','decision':'ACCEPT'}).status_code==409

def test_rule_review_cannot_approve():
    c=client('pharmacist');r=c.post('/rules/1/draft').json()
    assert c.post(f"/rules/{r['id']}/transition",json={'action':'PENDING_REVIEW','comments':'review'}).status_code==200
    assert c.post(f"/rules/{r['id']}/transition",json={'action':'APPROVED','comments':'unvalidated'}).status_code==409

@pytest.mark.parametrize('role',['physician','pharmacist','admin','researcher'])
def test_signed_session_survives_process_memory_loss(monkeypatch,role):
    from app import main
    monkeypatch.setenv('SERVERLESS_DEMO','true')
    monkeypatch.setenv('SESSION_SECRET','synthetic-test-session-key-32-chars-minimum')
    c=client(role);main.sessions.clear()
    assert c.get('/patients').status_code==200
    if role!='physician':
        assert c.post('/prescriptions',json={'drug':'Metformin','proposal':'demo','decision':'MODIFY'}).status_code==403
    c.post('/auth/logout')
    assert c.get('/patients').status_code==401

def test_signed_session_tampering_and_expiry(monkeypatch):
    from app.session_tokens import issue,verify
    monkeypatch.setenv('SESSION_SECRET','synthetic-test-session-key-32-chars-minimum')
    token=issue({'name':'demo-physician','role':'physician','expires':datetime.now(timezone.utc)+timedelta(hours=1)})
    assert verify(token)['role']=='physician'
    assert verify('bad'+token) is None
    assert verify(token[:-1]+('1' if token[-1]!='1' else '2')) is None
    expired=issue({'name':'demo-physician','role':'physician','expires':datetime.now(timezone.utc)-timedelta(seconds=1)})
    assert verify(expired) is None

def test_serverless_requires_strong_session_secret(monkeypatch):
    monkeypatch.setenv('SERVERLESS_DEMO','true')
    monkeypatch.setenv('SESSION_SECRET','short')
    assert TestClient(app).post('/auth/login',json={'role':'physician','password':'test-password-only'}).status_code==503
