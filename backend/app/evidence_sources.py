"""Allowlisted public retrieval. Licensed providers are never scraped."""
import hashlib
from html.parser import HTMLParser
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from .db import Session, Drug, EvidenceRecord

SOURCES={
    'uptodate_search':{'name':'UpToDate — Public Search','url':'https://www.uptodate.com/contents/search','category':'หน้าค้นหาสาธารณะ ไม่ใช่บทความเต็มหรือกฎขนาดยา','licensed':False},
    'uptodate':{'name':'UpToDate — Full Clinical Topics','url':'https://www.uptodate.com/contents/assessment-of-kidney-function','category':'ค่าไตและการตัดสินใจคลินิก','licensed':True},
    'lexidrug':{'name':'UpToDate Lexidrug','url':'https://www.wolterskluwer.com/en/solutions/uptodate','category':'Drug Information (DI)','licensed':True},
    'micromedex':{'name':'Micromedex','url':'https://www.merative.com/clinical-decision-support','category':'Drug Information (DI)','licensed':True},
    'niddk':{'name':'NIDDK','url':'https://www.niddk.nih.gov/health-information/professionals/clinical-tools-patient-management/kidney-disease/laboratory-evaluation/glomerular-filtration-rate-calculators','category':'สมการและการประเมินการทำงานของไต','licensed':False},
    'kdigo':{'name':'KDIGO CKD guidelines','url':'https://kdigo.org/guidelines/ckd-evaluation-and-management/','category':'แนวทางโรคไต','licensed':False},
    'nice':{'name':'NICE NG203','url':'https://www.nice.org.uk/guidance/ng203','category':'แนวทางโรคไตเรื้อรัง','licensed':False},
    'fda':{'name':'FDA Drugs@FDA','url':'https://www.accessdata.fda.gov/scripts/cder/daf/','category':'ค้นหาเอกสารกำกับยาทางการ ต้องเลือกฉลากฉบับจริงเพิ่มเติม','licensed':False},
    'nkf':{'name':'National Kidney Foundation (NKF)','url':'https://www.kidney.org/','category':'หลักการประเมินไต ต้องเลือกแนวทางต้นฉบับเพิ่มเติม','licensed':False},
    'dailymed':{'name':'DailyMed','url':'https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json','category':'ค้นหาฉลากยาต้นฉบับ (DI)','licensed':False},
    'pubmed':{'name':'PubMed','url':'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi','category':'ค้นหางานวิจัยและ PMID','licensed':False},
}

# Clinical reference priority is separate from retrieval permissions and evidence grade.
for key, source in SOURCES.items():
    source['priority'] = 1 if key in ('lexidrug','micromedex') else 2 if key in ('fda','dailymed') else 3 if key in ('kdigo','nkf') else None

class TextExtractor(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip():self.parts.append(data.strip())

def excerpt(raw,content_type):
    if not raw:return ''
    if content_type and 'html' in content_type:
        parser=TextExtractor();parser.feed(raw)
        return '\n'.join(parser.parts)[:1500]
    return raw[:1500]

def fetch_public(url):
    # No user-controlled destination, arbitrary URL, login cookie or bearer token.
    with httpx.Client(timeout=12,follow_redirects=False) as client:
        with client.stream('GET',url,headers={'User-Agent':'RenalSmartCDSS-EvidenceReview/0.2'}) as response:
            response.raise_for_status();chunks=[];size=0
            for chunk in response.iter_bytes():
                size+=len(chunk)
                if size>1_000_000:raise ValueError('SOURCE_TOO_LARGE: ใช้ลิงก์ต้นทางและทบทวนการนำเข้า')
                chunks.append(chunk)
            body=b''.join(chunks)
            if not body:raise ValueError('EMPTY_SOURCE')
            return dict(url=str(response.url),raw_text=body.decode(response.encoding or 'utf-8',errors='replace'),
                        raw_content=body,content_hash=hashlib.sha256(body).hexdigest(),content_type=response.headers.get('content-type',''))

def record_view(record):
    return dict(id=record.id,source_key=record.source_key,source_name=record.source_name,url=record.url,
                drug_id=record.drug_id,status=record.status,accessed_at=record.accessed_at,
                content_hash=record.content_hash,content_type=record.content_type,source_version=record.source_version,reviewer=record.reviewer,
                excerpt=excerpt(record.raw_text,record.content_type),error=record.error,
                clinical_status='PENDING_CLINICAL_VALIDATION')

class Retrieval(BaseModel):
    source_key:str
    drug_id:int|None=None
    query:str=Field(default='10.1056/NEJMoa2102953',max_length=200)

class ConflictFlag(BaseModel):
    reason:str=Field(min_length=1,max_length=2000)

def make_evidence_router(roles,audit,user):
    router=APIRouter()

    @router.get('/evidence/sources')
    def sources(u=Depends(user)):
        return [dict(key=key,**source,status='LICENSE_REQUIRED' if source['licensed'] else 'NOT_RETRIEVED') for key,source in SOURCES.items()]

    @router.get('/evidence')
    def records(u=Depends(user)):
        with Session() as s:return [record_view(r) for r in s.query(EvidenceRecord).order_by(EvidenceRecord.id.desc()).limit(100).all()]

    @router.post('/evidence/retrieve')
    def retrieve(p:Retrieval,u=Depends(roles('physician','pharmacist','admin'))):
        source=SOURCES.get(p.source_key)
        if not source:raise HTTPException(422,'แหล่งข้อมูลนี้ไม่ได้รับอนุญาต')
        with Session.begin() as s:
            url=source['url'];drug_id=None
            if p.source_key=='dailymed':
                drug=s.get(Drug,p.drug_id) if p.drug_id is not None else None
                if not drug:raise HTTPException(422,'เลือกยาจากฐานข้อมูลก่อนค้นหา DailyMed')
                drug_id=drug.id;url+='?'+urlencode({'drug_name':drug.name})
            if p.source_key=='uptodate_search':
                url+='?'+urlencode({'search':p.query.strip() or 'assessment of kidney function'})
            if p.source_key=='pubmed':
                if not p.query.strip():raise HTTPException(422,'กรอกคำค้นงานวิจัย')
                url+='?'+urlencode({'db':'pubmed','term':p.query,'retmode':'json','retmax':10})
            record=EvidenceRecord(source_key=p.source_key,source_name=source['name'],url=url,drug_id=drug_id,
                                  status='LICENSE_REQUIRED' if source['licensed'] else 'DRAFT')
            if source['licensed']:
                record.error='ยังไม่มีการเชื่อมต่อที่ได้รับอนุญาตของสถาบัน ไม่มีการดึงเนื้อหาหรือข้ามการเข้าสู่ระบบ'
            else:
                try:
                    data=fetch_public(url)
                    for key,value in data.items():setattr(record,key,value)
                except httpx.HTTPStatusError as error:
                    record.status='NETWORK_BLOCKED' if error.response.status_code in (401,403) else 'FETCH_FAILED'
                    record.error=f'HTTP_{error.response.status_code}: ยังไม่มีต้นฉบับที่นำเข้าได้'
                except (httpx.RequestError,ValueError) as error:
                    record.status='NETWORK_BLOCKED' if '403' in str(error) else 'FETCH_FAILED'
                    record.error='ไม่สามารถดึงต้นฉบับได้ ตรวจเครือข่าย/ข้อกำหนดแหล่งข้อมูลก่อนลองใหม่'
            s.add(record);s.flush()
            audit(s,u,'EVIDENCE_ACCESS','NOT_RETRIEVED',record.status,f'{record.source_name}; evidence={record.id}')
            return record_view(record)

    @router.post('/evidence/{record_id}/flag-conflict')
    def flag(record_id:int,p:ConflictFlag,u=Depends(roles('pharmacist','admin'))):
        if not p.reason.strip():raise HTTPException(422,'ระบุรายละเอียดที่ขัดแย้ง')
        with Session.begin() as s:
            record=s.get(EvidenceRecord,record_id)
            if not record:raise HTTPException(404)
            if not record.raw_text:raise HTTPException(409,'ยังไม่มีเนื้อหาต้นฉบับให้เปรียบเทียบ')
            previous=record.status;record.status='SOURCE_CONFLICT';record.error=p.reason.strip();record.reviewer=u['name']
            audit(s,u,'EVIDENCE_CONFLICT',previous,record.status,p.reason)
            return record_view(record)

    @router.get('/evidence/{record_id}/raw')
    def raw(record_id:int,u=Depends(user)):
        with Session() as s:
            record=s.get(EvidenceRecord,record_id)
            if not record:raise HTTPException(404)
            if record.raw_content is None:raise HTTPException(409,'ไม่มีต้นฉบับที่นำเข้าแล้ว')
            return Response(record.raw_content,media_type='application/octet-stream',headers={'X-Content-Type-Options':'nosniff','Content-Disposition':f'attachment; filename=evidence-{record_id}.txt'})

    return router
