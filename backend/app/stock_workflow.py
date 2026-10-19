"""Manual stock substitution workflow. No automatic clinical equivalence."""
import json
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .db import Session, Drug, Prescription, StockAlternative
from .clinical import RenalInput, calculate

PENDING_STOCK=('WAITING_STOCK_ALTERNATIVE','ALTERNATIVE_PROPOSED')

def drug_view(drug):
    return dict(id=drug.id,name=drug.name,stock_status=drug.stock_status,
                clinical_status=drug.status,label='SYNTHETIC INVENTORY')

def prescription_view(s,record):
    proposals=[]
    for a in s.query(StockAlternative).filter_by(prescription_id=record.id).all():
        d=s.get(Drug,a.drug_id)
        proposals.append(dict(id=a.id,drug_id=a.drug_id,drug=d.name,stock_status=d.stock_status,
                              indication=a.indication,rationale=a.rationale,status=a.status,
                              proposed_by=a.proposed_by,created_at=a.created_at,
                              clinical_status='PENDING_CLINICAL_VALIDATION',dose=None))
    return dict(id=record.id,patient=record.patient,drug=record.drug,proposal=record.proposal,
                decision=record.decision,reason=record.reason,status=record.status,
                created_at=record.created_at,finalized_at=record.finalized_at,
                stock_alternative_id=record.stock_alternative_id,
                source_snapshot=json.loads(record.source_snapshot),stock_alternatives=proposals)

class StockUpdate(BaseModel):
    status:Literal['IN_STOCK','OUT_OF_STOCK']

class AlternativeProposal(BaseModel):
    drug_id:int
    indication:str=Field(min_length=1,max_length=500)
    rationale:str=Field(min_length=10,max_length=2000)

class AlternativeDecision(BaseModel):
    action:Literal['ACCEPT','DECLINE']
    proposal:str=Field(default='',max_length=1000)
    reason:str=Field(min_length=1,max_length=2000)
    override:bool=False

def make_stock_router(roles,audit):
    router=APIRouter()

    @router.get('/inventory')
    def inventory(u=Depends(roles('physician','pharmacist','admin'))):
        with Session() as s:return [drug_view(d) for d in s.query(Drug).order_by(Drug.id).all()]

    @router.post('/inventory/{drug_id}')
    def update_stock(drug_id:int,p:StockUpdate,u=Depends(roles('pharmacist','admin'))):
        with Session.begin() as s:
            d=s.get(Drug,drug_id)
            if not d:raise HTTPException(404,'ไม่พบยาในคลังจำลอง')
            previous=d.stock_status;d.stock_status=p.status
            audit(s,u,'STOCK_CHANGED',previous,p.status,d.name)
            return drug_view(d)

    @router.post('/prescriptions/{record_id}/stock-alternatives')
    def propose(record_id:int,p:AlternativeProposal,u=Depends(roles('pharmacist'))):
        if not p.indication.strip() or len(p.rationale.strip())<10:
            raise HTTPException(422,'ระบุข้อบ่งใช้และเหตุผลทางคลินิกเพื่อให้แพทย์ทบทวน')
        with Session.begin() as s:
            r=s.get(Prescription,record_id);d=s.get(Drug,p.drug_id)
            if not r or not d:raise HTTPException(404)
            if r.status not in PENDING_STOCK:raise HTTPException(409,'รายการนี้ไม่ได้รอทางเลือกกรณียาขาดคลัง')
            if d.stock_status!='IN_STOCK':raise HTTPException(409,'ยาที่เสนอไม่มีในคลังจำลอง')
            if d.name==r.drug:raise HTTPException(422,'เลือกยาที่ต่างจากรายการเดิม')
            a=StockAlternative(prescription_id=r.id,drug_id=d.id,proposed_by=u['name'],
                               indication=p.indication.strip(),rationale=p.rationale.strip())
            s.add(a);s.flush()
            previous=r.status;r.status='ALTERNATIVE_PROPOSED'
            audit(s,u,'PHARMACIST_STOCK_ALTERNATIVE',previous,r.status,
                  f'proposal={a.id}; drug={d.name}; indication={a.indication}; {a.rationale}',r.id)
            return {'id':a.id,'status':a.status,'dose':None,'clinical_status':'PENDING_CLINICAL_VALIDATION'}

    @router.post('/prescriptions/{record_id}/stock-alternatives/{alternative_id}/decision')
    def decide(record_id:int,alternative_id:int,p:AlternativeDecision,u=Depends(roles('physician'))):
        if not p.reason.strip():raise HTTPException(422,'ระบุเหตุผลการตัดสินใจของแพทย์')
        with Session.begin() as s:
            r=s.get(Prescription,record_id);a=s.get(StockAlternative,alternative_id)
            if not r or not a or a.prescription_id!=record_id:raise HTTPException(404)
            if r.status not in PENDING_STOCK or a.status!='PROPOSED':raise HTTPException(409,'รายการได้รับการตัดสินใจแล้ว')
            if p.action=='DECLINE':
                a.status='DECLINED';s.flush()
                remaining=s.query(StockAlternative).filter_by(prescription_id=r.id,status='PROPOSED').count()
                previous=r.status;r.status='ALTERNATIVE_PROPOSED' if remaining else 'WAITING_STOCK_ALTERNATIVE'
                audit(s,u,'PHYSICIAN_DECLINED_STOCK_ALTERNATIVE',previous,r.status,p.reason,r.id)
                return {'status':r.status}
            if not p.proposal.strip():raise HTTPException(422,'แพทย์ต้องกรอกข้อเสนอยาและวิธีใช้ของตนเองก่อนยืนยัน')
            drug=s.get(Drug,a.drug_id)
            if drug.stock_status!='IN_STOCK':raise HTTPException(409,'ยาทางเลือกขาดคลังแล้ว กรุณาให้เภสัชกรเสนอใหม่')
            snapshot=json.loads(r.source_snapshot)
            snapshot['calculation']=calculate(RenalInput(**snapshot))
            if snapshot['calculation']['status']!='SIMULATION' and not p.override:
                raise HTTPException(409,'ต้องตรวจสอบข้อมูลไต หรือแพทย์ยืนยัน Override พร้อมเหตุผล')
            previous=r.status
            changed=s.query(Prescription).filter(Prescription.id==r.id,Prescription.status.in_(PENDING_STOCK)).update({'status':'REPLACED_BY_PHYSICIAN'})
            if changed!=1:raise HTTPException(409,'มีการตัดสินใจรายการนี้แล้ว')
            a.status='SELECTED'
            for other in s.query(StockAlternative).filter_by(prescription_id=r.id,status='PROPOSED').all():
                if other.id!=a.id:other.status='NOT_SELECTED'
            final=Prescription(patient=r.patient,department=r.department,drug=drug.name,
                               proposal=p.proposal.strip(),decision='OVERRIDE' if p.override else 'STOCK_ALTERNATIVE',
                               reason=p.reason.strip(),status='PHYSICIAN_FINALIZED',
                               finalized_at=datetime.now(timezone.utc),source_snapshot=json.dumps(snapshot),stock_alternative_id=a.id)
            s.add(final);s.flush()
            audit(s,u,'PHYSICIAN_SELECTED_STOCK_ALTERNATIVE',previous,'REPLACED_BY_PHYSICIAN',
                  f'proposal={a.id}; replacement={final.id}; {p.reason}',r.id)
            audit(s,u,'PHYSICIAN_FINALIZED','DRAFT',final.status,p.reason,final.id)
            return {'id':final.id,'status':final.status,'drug':drug.name}

    return router
