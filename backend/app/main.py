import os, secrets, hashlib, json
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Depends, HTTPException, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from .db import Session, Drug, Rule, Prescription, Audit, Patient
from .clinical import RenalInput, calculate, evaluate
from . import session_tokens
app=FastAPI(title='Renal Smart CDSS — SYNTHETIC DATA')
app.add_middleware(CORSMiddleware,allow_origins=[os.getenv('FRONTEND_ORIGIN','http://localhost:3000')],allow_credentials=True,allow_methods=['GET','POST'],allow_headers=['Content-Type'])
sessions={}
def user(session: str|None=Cookie(default=None)):
    entry=session_tokens.verify(session or '') if session_tokens.enabled() else sessions.get(session or '')
    if not entry or entry['expires']<datetime.now(timezone.utc): raise HTTPException(401,'กรุณาเข้าสู่ระบบ')
    return entry

def roles(*allowed):
    def check(u=Depends(user)):
        if u['role'] not in allowed: raise HTTPException(403,'ไม่มีสิทธิ์')
        return u
    return check

def audit(s,u,action,previous,new,comments='',record_id=None):
    s.add(Audit(user=u['name'],action=action,previous=previous,new=new,comments=comments,record_id=record_id))
class Login(BaseModel):
    role:str
    password:str
@app.post('/auth/login')
def login(p:Login,response:Response):
    expected=os.getenv('DEMO_PASSWORD')
    if not expected: raise HTTPException(503,'ตั้งค่า DEMO_PASSWORD ก่อนเริ่มใช้งาน')
    if p.role not in ['physician','pharmacist','admin','researcher'] or not secrets.compare_digest(p.password,expected): raise HTTPException(401,'ข้อมูลเข้าสู่ระบบไม่ถูกต้อง')
    entry={'name':'demo-'+p.role,'role':p.role,'expires':datetime.now(timezone.utc)+timedelta(hours=4)}
    if session_tokens.enabled():
        try: token=session_tokens.issue(entry)
        except ValueError: raise HTTPException(503,'ตั้งค่า SESSION_SECRET อย่างน้อย 32 ตัวอักษร')
    else:
        token=secrets.token_urlsafe(32)
        sessions[token]=entry
    response.set_cookie('session',token,httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE','false')=='true',max_age=14400)
    return {'role':p.role,'mode':'SIMULATION'}
@app.post('/auth/logout')
def logout(response:Response,session:str|None=Cookie(default=None)):
    sessions.pop(session or '',None); response.delete_cookie('session'); return {'ok':True}
@app.get('/health')
def health():
    with Session() as s: s.execute(select(Drug).limit(1))
    return {'status':'ok','mode':'SYNTHETIC DATA'}
@app.get('/patients')
def patients(u=Depends(user)):
    with Session() as s: return [json.loads(p.source) for p in s.query(Patient).all()]
@app.post('/renal/calculate')
def renal(p:RenalInput,u=Depends(user)): return calculate(p)
class Assessment(BaseModel):
    patient:RenalInput
    drug:str
    indication:str|None=None
@app.post('/assess')
def assess(p:Assessment,u=Depends(user)): return evaluate(p.patient,indication=p.indication)
@app.get('/drugs')
def drugs(u=Depends(user)):
    with Session() as s: return [{'id':d.id,'name':d.name,'status':d.status,'evidence':json.loads(d.evidence)} for d in s.query(Drug).all()]
class Decision(BaseModel):
    drug:str=Field(min_length=1,max_length=100)
    proposal:str=Field(min_length=1,max_length=1000)
    decision:str
    reason:str=Field(default='',max_length=2000)
    patient_input:RenalInput|None=None
@app.post('/prescriptions')
def prescribe(p:Decision,u=Depends(roles('physician'))):
    if p.decision not in ['MODIFY','OVERRIDE','ACCEPT','ALTERNATIVE']: raise HTTPException(422,'Invalid decision')
    if p.decision in ['ACCEPT','ALTERNATIVE']: raise HTTPException(409,'No validated recommendation or alternative available')
    if p.decision=='OVERRIDE' and not p.reason.strip(): raise HTTPException(422,'ต้องระบุเหตุผล')
    with Session.begin() as s:
        source=s.get(Patient,'SYN-001')
        if not source: raise HTTPException(409,'Seed synthetic patient first')
        snapshot=json.loads(source.source)
        if p.patient_input: snapshot.update(p.patient_input.model_dump(mode='json'))
        snapshot['calculation']=calculate(RenalInput(**snapshot))
        record=Prescription(**p.model_dump(exclude={'patient_input'}),source_snapshot=json.dumps(snapshot)); s.add(record); s.flush()
        audit(s,u,'PHYSICIAN_'+p.decision,'DRAFT','SUBMITTED',p.reason,record.id)
        return {'id':record.id,'status':record.status}
@app.get('/prescriptions')
def prescriptions(u=Depends(roles('physician','pharmacist','admin'))):
    with Session() as s: return [dict(id=p.id,patient=p.patient,drug=p.drug,proposal=p.proposal,decision=p.decision,reason=p.reason,status=p.status,created_at=p.created_at,source_snapshot=json.loads(p.source_snapshot)) for p in s.query(Prescription).all()]
class Review(BaseModel):
    action:str
    comments:str=Field(min_length=1,max_length=2000)
@app.post('/prescriptions/{id}/review')
def review(id:int,p:Review,u=Depends(roles('pharmacist'))):
    if p.action not in ['VERIFIED','REJECTED','CLARIFICATION','MODIFICATION','SAFETY_PROBLEM']: raise HTTPException(422,'Invalid action')
    with Session.begin() as s:
        r=s.get(Prescription,id)
        if not r: raise HTTPException(404)
        if r.status!='SUBMITTED': raise HTTPException(409,'รายการได้รับการตรวจสอบแล้ว')
        audit(s,u,'PHARMACIST_'+p.action,r.status,p.action,p.comments,r.id);r.status=p.action
    return {'status':p.action}
@app.get('/audit')
def audits(u=Depends(roles('admin','pharmacist'))):
    with Session() as s: return [dict(id=a.id,user=a.user,action=a.action,previous=a.previous,new=a.new,comments=a.comments,record_id=a.record_id,timestamp=a.timestamp) for a in s.query(Audit).order_by(Audit.id.desc()).all()]
@app.get('/rules')
def rules(u=Depends(user)):
    with Session() as s: return [dict(id=r.id,drug_id=r.drug_id,version=r.version,status=r.status,specification=json.loads(r.specification),reviewer=r.reviewer) for r in s.query(Rule).all()]
@app.post('/rules/{drug_id}/draft')
def draft(drug_id:int,u=Depends(roles('pharmacist','admin'))):
    with Session.begin() as s:
        if not s.get(Drug,drug_id): raise HTTPException(404)
        version=s.query(Rule).filter_by(drug_id=drug_id).count()+1
        r=Rule(drug_id=drug_id,version=version);s.add(r);s.flush();audit(s,u,'RULE_DRAFT','NONE','DRAFT');return {'id':r.id,'version':version}
@app.post('/rules/{id}/transition')
def transition(id:int,p:Review,u=Depends(roles('pharmacist','admin'))):
    transitions={'DRAFT':'PENDING_REVIEW','PENDING_REVIEW':'APPROVED','APPROVED':'ACTIVE','ACTIVE':'RETIRED'}
    with Session.begin() as s:
        r=s.get(Rule,id)
        if not r: raise HTTPException(404)
        if transitions.get(r.status)!=p.action: raise HTTPException(409,'Invalid transition')
        if p.action in ['APPROVED','ACTIVE']: raise HTTPException(409,'Clinical validation and institutional approval not configured; activation blocked')
        audit(s,u,'RULE_TRANSITION',r.status,p.action,p.comments,r.id);r.status=p.action
    return {'status':p.action}
class Capture(BaseModel):
    patient_id:str
    expected_patient_id:str
    confidence:float=Field(ge=0,le=1)
    fields:dict
    monitoring:bool=False
@app.post('/agent/capture')
def capture(p:Capture,u=Depends(roles('physician'))):
    valid=p.monitoring and p.patient_id==p.expected_patient_id and p.patient_id.startswith('SYN-') and p.confidence>=0.98 and all(k in p.fields for k in ['scr','unit','collected_at'])
    return {'status':'SIMULATION' if valid else 'VERIFICATION_REQUIRED','clinical_recommendations_enabled':False,'retained_screenshot':False}
@app.get('/analytics')
def analytics(start:str|None=None,end:str|None=None,department:str|None=None,u=Depends(user)):
    with Session() as s:
        q=s.query(Prescription)
        try:
            if start:q=q.filter(Prescription.created_at>=datetime.fromisoformat(start))
            if end:q=q.filter(Prescription.created_at<datetime.fromisoformat(end)+timedelta(days=1))
        except ValueError:raise HTTPException(422,'Invalid date')
        if department:q=q.filter_by(department=department)
        rows=q.all(); n=len(rows)
        return {'label':'SYNTHETIC DATA','screened':n,'override_rate':sum(r.decision=='OVERRIDE' for r in rows)/n if n else 0,'verification_rate':sum(r.status=='VERIFIED' for r in rows)/n if n else 0,'renal_alerts':None,'dose_adjustments':0,'alternatives':0,'acceptance_rate':None,'medication_error_rate':None,'ocr_accuracy':None,'review_time':None,'satisfaction':None,'note':'null = ยังไม่มีข้อมูลที่วัดได้'}
@app.get('/analytics/export')
def export(u=Depends(roles('researcher','admin'))):
    import csv,io
    out=io.StringIO();w=csv.writer(out);w.writerow(['SYNTHETIC DATA','id','department','status'])
    with Session() as s:
        for r in s.query(Prescription):w.writerow(['SYNTHETIC DATA',r.id,r.department,r.status])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=synthetic.csv'})

@app.post('/drugs/{id}/retrieve')
def retrieve(id:int,u=Depends(roles('pharmacist','admin'))):
    from .evidence import DailyMedProvider
    import httpx
    with Session.begin() as s:
        drug=s.get(Drug,id)
        if not drug:raise HTTPException(404)
        try: evidence=DailyMedProvider().retrieve(drug.name)
        except httpx.HTTPError:raise HTTPException(502,'DailyMed retrieval unavailable; no evidence imported')
        drug.evidence=json.dumps(evidence);drug.status='PENDING_CLINICAL_VALIDATION'
        audit(s,u,'EVIDENCE_RETRIEVAL','NONE','DRAFT',drug.name)
        return evidence
