import hashlib
import httpx
import pytest
from test_safety import db,client
from app.db import Session,Rule,Drug
from app import evidence_sources

@pytest.mark.parametrize('key',['uptodate','lexidrug','micromedex'])
def test_licensed_source_never_fetched_or_marked_retrieved(monkeypatch,key):
    def forbidden(*args):raise AssertionError('Licensed content must not be requested')
    monkeypatch.setattr(evidence_sources,'fetch_public',forbidden)
    c=client('physician');r=c.post('/evidence/retrieve',json={'source_key':key})
    assert r.status_code==200
    data=r.json();assert data['status']=='LICENSE_REQUIRED'
    assert data['content_hash'] is None and data['excerpt']==''
    assert c.get(f"/evidence/{data['id']}/raw").status_code==409

def fixture_fetch(url):
    body=b'<html><script>hidden script</script><p>SYNTHETIC public evidence fixture</p></html>'
    return dict(url=url,raw_text=body.decode(),raw_content=body,content_hash=hashlib.sha256(body).hexdigest(),content_type='text/html')

def test_public_import_retains_provenance_but_never_activates(monkeypatch):
    monkeypatch.setattr(evidence_sources,'fetch_public',fixture_fetch)
    c=client('physician');data=c.post('/evidence/retrieve',json={'source_key':'niddk'}).json()
    assert data['status']=='DRAFT'
    assert data['source_name']=='NIDDK' and data['url'].startswith('https://www.niddk.nih.gov/')
    assert data['accessed_at'] and data['source_version'] is None and data['reviewer'] is None
    assert data['excerpt']=='SYNTHETIC public evidence fixture'
    assert data['clinical_status']=='PENDING_CLINICAL_VALIDATION'
    raw=c.get(f"/evidence/{data['id']}/raw")
    assert hashlib.sha256(raw.content).hexdigest()==data['content_hash']
    assert raw.headers['x-content-type-options']=='nosniff'
    with Session() as s:
        assert s.query(Rule).count()==0
        assert not any(d.status=='ACTIVE' for d in s.query(Drug))

def test_network_denial_recorded_without_claiming_content(monkeypatch):
    def denied(url):raise httpx.ProxyError('CONNECT tunnel failed 403 Forbidden')
    monkeypatch.setattr(evidence_sources,'fetch_public',denied)
    data=client('physician').post('/evidence/retrieve',json={'source_key':'kdigo'}).json()
    assert data['status']=='NETWORK_BLOCKED'
    assert data['content_hash'] is None and data['excerpt']==''

def test_allowlist_and_role_checks(monkeypatch):
    monkeypatch.setattr(evidence_sources,'fetch_public',fixture_fetch)
    assert client('researcher').post('/evidence/retrieve',json={'source_key':'niddk'}).status_code==403
    c=client('physician')
    assert c.post('/evidence/retrieve',json={'source_key':'https://untrusted.example'}).status_code==422
    assert c.post('/evidence/retrieve',json={'source_key':'dailymed'}).status_code==422
    assert c.post('/evidence/retrieve',json={'source_key':'dailymed','drug_id':1}).json()['url'].endswith('drug_name=Metformin')

def test_source_conflict_needs_reviewer_and_does_not_activate(monkeypatch):
    monkeypatch.setattr(evidence_sources,'fetch_public',fixture_fetch)
    doctor=client('physician');pharmacist=client('pharmacist')
    data=doctor.post('/evidence/retrieve',json={'source_key':'nice'}).json()
    url=f"/evidence/{data['id']}/flag-conflict"
    assert doctor.post(url,json={'reason':'conflict fixture'}).status_code==403
    flagged=pharmacist.post(url,json={'reason':'ข้อแนะนำต้นฉบับขัดแย้ง ต้องตรวจสอบโดยผู้เชี่ยวชาญ'}).json()
    assert flagged['status']=='SOURCE_CONFLICT'
    assert flagged['reviewer']=='demo-pharmacist'
    assert flagged['clinical_status']=='PENDING_CLINICAL_VALIDATION'
    assert any(a['action']=='EVIDENCE_CONFLICT' for a in pharmacist.get('/audit').json())


def test_uptodate_public_search_is_not_treated_as_licensed_article(monkeypatch):
    monkeypatch.setattr(evidence_sources,'fetch_public',fixture_fetch)
    c=client('physician')
    sources={v['key']:v for v in c.get('/evidence/sources').json()}
    assert sources['uptodate_search']['licensed'] is False
    assert sources['uptodate']['licensed'] is True
    data=c.post('/evidence/retrieve',json={'source_key':'uptodate_search','query':'renal impairment'}).json()
    assert data['status']=='DRAFT'
    assert data['url']=='https://www.uptodate.com/contents/search?search=renal+impairment'
    assert data['clinical_status']=='PENDING_CLINICAL_VALIDATION'


def test_reference_priorities_and_unverified_rule_fields():
    c=client('pharmacist')
    sources={v['key']:v for v in c.get('/evidence/sources').json()}
    assert sources['lexidrug']['priority']==sources['micromedex']['priority']==1
    assert sources['fda']['priority']==sources['dailymed']['priority']==2
    assert sources['kdigo']['priority']==sources['nkf']['priority']==3
    c.post('/rules/1/draft')
    rule=c.get('/rules').json()[0]
    assert rule['status']=='DRAFT'
    spec=rule['specification']
    assert spec['generic_name']=='Metformin'
    assert spec['renal_measure'] is None and spec['adjusted_dose'] is None
    assert spec['evidence_level'] is None and spec['reviewer'] is None
    assert spec['sources']==[] and spec['thresholds']==[]
