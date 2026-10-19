import os
os.environ['DATABASE_URL']='sqlite:////tmp/renal-smart-test.db'
os.environ['DEMO_PASSWORD']='test-password-only'
from datetime import datetime,timezone,timedelta
import pytest
from fastapi.testclient import TestClient
from app.db import Base,engine,seed,Session,Audit,Prescription
from app.main import app
from app.clinical import RenalInput,calculate,evaluate
METFORMIN_PRODUCT='Metformin TAB 500 MG (MIFORMIN-500) [1000997]'
@pytest.fixture(autouse=True)
def db():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine);seed()
def patient(**kw):
    data=dict(age=65,weight_kg=60,sex='male',scr=1.5,collected_at=datetime.now(timezone.utc),verified=True,actual_weight_appropriate=True,stable=True,dialysis=False)
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
    payload=dict(drug=METFORMIN_PRODUCT,proposal='ข้อเสนอจำลอง',decision='OVERRIDE',reason='')
    assert doctor.post('/prescriptions',json=payload).status_code==422
    payload['reason']='ทบทวนโดยแพทย์';r=doctor.post('/prescriptions',json=payload);assert r.status_code==200
    id=r.json()['id']
    assert doctor.post(f'/prescriptions/{id}/review',json={'action':'VERIFIED','comments':'test'}).status_code==403
    assert r.json()['status']=='PHYSICIAN_FINALIZED'
    assert pharmacist.post(f'/prescriptions/{id}/review',json={'action':'REJECTED','comments':'ข้อมูลไม่เพียงพอ'}).status_code==409
    # Historical submissions remain reviewable; new decisions do not wait for review.
    with Session.begin() as s:
        legacy=Prescription(drug=METFORMIN_PRODUCT,proposal='legacy synthetic',decision='MODIFY',status='SUBMITTED');s.add(legacy);s.flush();legacy_id=legacy.id
    assert pharmacist.post(f'/prescriptions/{legacy_id}/review',json={'action':'REJECTED','comments':'ข้อมูลไม่เพียงพอ'}).json()['status']=='REJECTED'
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
    r=c.post('/prescriptions',json={'drug':METFORMIN_PRODUCT,'proposal':'synthetic only','decision':'MODIFY'}).json()
    p=client('pharmacist');record=p.get('/prescriptions').json()[0]
    assert record['source_snapshot']['id']=='SYN-001'
    assert 'calculation' in record['source_snapshot']
    payload={'action':'CLARIFICATION','comments':'ขอข้อมูลเพิ่ม'}
    assert record['status']=='PHYSICIAN_FINALIZED'
    assert record['finalized_at'] is not None
    assert p.post(f"/prescriptions/{r['id']}/review",json=payload).status_code==409
    assert p.get('/audit').json()[0]['record_id']==r['id']

def test_no_unvalidated_acceptance():
    c=client('physician')
    assert c.post('/prescriptions',json={'drug':METFORMIN_PRODUCT,'proposal':'demo','decision':'ACCEPT'}).status_code==409

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
        assert c.post('/prescriptions',json={'drug':METFORMIN_PRODUCT,'proposal':'demo','decision':'MODIFY'}).status_code==403
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

# Fixed numerical fixtures from independent high-precision decimal evaluation
# of the published CKD-EPI 2021 specification, including both sides of kappa.
@pytest.mark.parametrize('sex,age,scr,expected',[
    ('female',65,1.5,38.43),('male',65,1.5,51.35),
    ('female',40,.69,112.44),('female',40,.7,112.05),('female',40,.71,110.16),
    ('male',40,.89,111.10),('male',40,.9,110.73),('male',40,.91,109.27),
    ('female',18,.5,139.34),('male',90,3,19.13),
])
def test_ckd_epi_2021_reference_values(sex,age,scr,expected):
    r=calculate(patient(sex=sex,age=age,scr=scr))
    assert r['egfr']==expected
    assert r['egfr_unit']=='mL/min/1.73m²'
    assert r['unit']=='mL/min'

def test_egfr_calculated_not_copied_from_reported_lab():
    first=calculate(patient(sex='female',egfr=99))
    second=calculate(patient(sex='female',egfr=None))
    assert first['egfr']==second['egfr']==38.43
    assert first['egfr_reported']==99
    assert second['egfr_reported'] is None

def test_egfr_unit_conversion():
    mg=calculate(patient(sex='female',scr=1.5))
    umol=calculate(patient(sex='female',scr=132.6,unit='µmol/L'))
    assert mg['egfr']==umol['egfr']==38.43
    assert mg['crcl']==umol['crcl']==35.42

@pytest.mark.parametrize('kw',[{'stable':False},{'dialysis':True},{'dialysis':None},{'verified':False},{'collected_at':datetime.now(timezone.utc)-timedelta(days=3)}])
def test_no_calculated_values_when_context_is_unsafe(kw):
    r=calculate(patient(**kw))
    assert 'egfr' not in r and 'crcl' not in r

@pytest.mark.parametrize('scr',[0,-1,None,float('nan'),float('inf')])
def test_invalid_scr_rejected(scr):
    with pytest.raises(ValueError):patient(scr=scr)

@pytest.mark.parametrize('scr,unit',[(5e-324,'µmol/L'),(5e-324,'mg/dL')])
def test_numeric_underflow_and_overflow_require_verification(scr,unit):
    r=calculate(patient(scr=scr,unit=unit))
    assert r['status']=='VERIFICATION_REQUIRED'
    assert 'crcl' not in r and 'egfr' not in r

def test_egfr_does_not_use_weight_but_crcl_does():
    lighter=calculate(patient(weight_kg=60))
    heavier=calculate(patient(weight_kg=80))
    assert lighter['egfr']==heavier['egfr']
    assert lighter['crcl']!=heavier['crcl']

def test_adult_equations_reject_child_age():
    with pytest.raises(ValueError):patient(age=17)


def test_missing_stability_or_dialysis_context_is_not_assumed_safe():
    data=patient().model_dump()
    data.pop('stable');data.pop('dialysis')
    result=calculate(RenalInput(**data))
    assert result['status']=='CLINICAL_REVIEW_REQUIRED'
    assert 'crcl' not in result and 'egfr' not in result
