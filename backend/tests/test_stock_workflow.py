from test_safety import db, client, patient
from app.db import Session, Prescription

def request_stock(doctor):
    response=doctor.post('/prescriptions',json={'drug':'Sitagliptin','proposal':'ข้อเสนอแพทย์ในข้อมูลจำลอง','decision':'MODIFY'})
    assert response.status_code==200,response.text
    assert response.json()['status']=='WAITING_STOCK_ALTERNATIVE'
    return response.json()['id']

def offer(pharmacist,record,drug_id=1):
    response=pharmacist.post(f'/prescriptions/{record}/stock-alternatives',json={'drug_id':drug_id,'indication':'เบาหวานชนิดที่ 2','rationale':'ข้อเสนอเภสัชกรในกรณีจำลอง ให้แพทย์ทบทวนความเหมาะสมทางคลินิก'})
    return response

def test_physician_finalizes_without_pharmacist_gate():
    doctor=client('physician');r=doctor.post('/prescriptions',json={'drug':'Metformin','proposal':'manual synthetic proposal','decision':'MODIFY'})
    assert r.json()['status']=='PHYSICIAN_FINALIZED'
    records=doctor.get('/prescriptions').json()
    assert records[0]['finalized_at'] is not None
    assert records[0]['stock_alternatives']==[]
    assert doctor.get('/analytics').json()['physician_finalized']==1
    assert doctor.get('/analytics').json()['stock_pending']==0

def test_stock_alternative_requires_physician_choice_and_manual_proposal():
    doctor=client('physician');pharmacist=client('pharmacist');record=request_stock(doctor)
    response=offer(pharmacist,record);assert response.status_code==200
    a=response.json();assert a['dose'] is None and a['clinical_status']=='PENDING_CLINICAL_VALIDATION'
    assert doctor.get('/prescriptions').json()[0]['status']=='ALTERNATIVE_PROPOSED'
    endpoint=f"/prescriptions/{record}/stock-alternatives/{a['id']}/decision"
    assert pharmacist.post(endpoint,json={'action':'ACCEPT','reason':'test','proposal':'manual'}).status_code==403
    assert doctor.post(endpoint,json={'action':'ACCEPT','reason':'ทบทวนแล้ว'}).status_code==422
    final=doctor.post(endpoint,json={'action':'ACCEPT','reason':'แพทย์ทบทวนในข้อมูลจำลองแล้ว','proposal':'ข้อเสนอใหม่โดยแพทย์ ไม่มีขนาดยาจากระบบ'})
    assert final.status_code==200,final.text
    assert final.json()['status']=='PHYSICIAN_FINALIZED'
    records=doctor.get('/prescriptions').json()
    assert records[0]['status']=='REPLACED_BY_PHYSICIAN'
    assert records[1]['stock_alternative_id']==a['id']
    assert records[1]['source_snapshot']['id']=='SYN-001'
    assert doctor.post(endpoint,json={'action':'ACCEPT','reason':'replay','proposal':'manual'}).status_code==409
    actions=[a['action'] for a in pharmacist.get('/audit').json()]
    assert 'PHARMACIST_STOCK_ALTERNATIVE' in actions
    assert 'PHYSICIAN_SELECTED_STOCK_ALTERNATIVE' in actions
    assert doctor.get('/analytics').json()['stock_pending']==0

def test_physician_can_decline_without_finalizing():
    doctor=client('physician');pharmacist=client('pharmacist');record=request_stock(doctor)
    a=offer(pharmacist,record).json()
    result=doctor.post(f"/prescriptions/{record}/stock-alternatives/{a['id']}/decision",json={'action':'DECLINE','reason':'ต้องพิจารณาข้อบ่งใช้อื่นเพิ่มเติม'})
    assert result.json()['status']=='WAITING_STOCK_ALTERNATIVE'
    assert len(doctor.get('/prescriptions').json())==1
    assert doctor.get('/prescriptions').json()[0]['stock_alternatives'][0]['status']=='DECLINED'

def test_stock_checked_at_proposal_and_physician_confirmation():
    doctor=client('physician');pharmacist=client('pharmacist');record=request_stock(doctor)
    assert offer(pharmacist,record,drug_id=2).status_code==409
    a=offer(pharmacist,record).json()
    assert pharmacist.post('/inventory/1',json={'status':'OUT_OF_STOCK'}).status_code==200
    assert doctor.post(f"/prescriptions/{record}/stock-alternatives/{a['id']}/decision",json={'action':'ACCEPT','reason':'manual review','proposal':'manual plan'}).status_code==409
    assert len(doctor.get('/prescriptions').json())==1

def test_roles_and_stock_request_scope():
    doctor=client('physician');pharmacist=client('pharmacist')
    assert doctor.post('/inventory/1',json={'status':'OUT_OF_STOCK'}).status_code==403
    record=request_stock(doctor)
    assert doctor.post(f'/prescriptions/{record}/stock-alternatives',json={'drug_id':1,'indication':'diabetes','rationale':'manual proposal'}).status_code==403
    ready=doctor.post('/prescriptions',json={'drug':'Metformin','proposal':'manual synthetic','decision':'MODIFY'}).json()['id']
    assert offer(pharmacist,ready).status_code==409
    assert doctor.post('/prescriptions',json={'drug':'unknown','proposal':'manual','decision':'MODIFY'}).status_code==422

def test_unsafe_renal_context_requires_physician_override():
    doctor=client('physician');data=patient(stable=False).model_dump(mode='json')
    payload={'drug':'Metformin','proposal':'manual synthetic','decision':'MODIFY','patient_input':data}
    assert doctor.post('/prescriptions',json=payload).status_code==409
    payload.update(decision='OVERRIDE',reason='แพทย์ทบทวนข้อจำกัดในกรณีจำลอง')
    assert doctor.post('/prescriptions',json=payload).json()['status']=='PHYSICIAN_FINALIZED'
