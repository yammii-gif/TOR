"""PDF documents are reference data, never executable instructions or dose rules."""
import hashlib
import io
import json
from datetime import datetime,timezone
from urllib.parse import urlsplit
import httpx
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import Response
from pydantic import BaseModel,Field
from sqlalchemy.orm import defer
from .db import Session,EvidenceRecord

MAX_BYTES=8*1024*1024
PUBLIC_HOSTS={'kdigo.org','www.nice.org.uk','www.kidney.org','www.niddk.nih.gov'}
CATALOG=[
    {'name':'KDIGO','url':'https://kdigo.org/guidelines/','scope':'แนวทางโรคไตและโรคร่วม'},
    {'name':'NICE NG203','url':'https://www.nice.org.uk/guidance/ng203','scope':'CKD: assessment and management'},
    {'name':'NKF / KDOQI','url':'https://www.kidney.org/','scope':'แนวทางและหลักการประเมินไต'},
    {'name':'NIDDK','url':'https://www.niddk.nih.gov/','scope':'การประเมินไตและ clinical tools ไม่ใช่กฎขนาดยา'},
]


def validate_public_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in PUBLIC_HOSTS or p.username or p.password or p.port not in (None,443):
        raise ValueError('ใช้เฉพาะ HTTPS ของแหล่งสาธารณะที่กำหนด ไม่รับบทความที่ต้องมีสิทธิ์')
    return url


def fetch_pdf(url):
    validate_public_url(url)
    with httpx.Client(timeout=25,follow_redirects=False) as client:
        for _ in range(5):
            with client.stream('GET',url,headers={'User-Agent':'RenalSmartCDSS-GuidelineReview/2.2'}) as response:
                if response.status_code in (301,302,303,307,308):
                    from urllib.parse import urljoin
                    url=validate_public_url(urljoin(url,response.headers.get('location','')))
                    continue
                response.raise_for_status();chunks=[];size=0
                for chunk in response.iter_bytes():
                    size+=len(chunk)
                    if size>MAX_BYTES:raise ValueError('PDF เกิน 8 MB')
                    chunks.append(chunk)
                content=b''.join(chunks)
                if not content.startswith(b'%PDF-'):raise ValueError('ได้หน้าค้นหา/HTML ไม่ใช่ PDF ฉบับเต็ม')
                return content,str(response.url)
    raise ValueError('redirect มากเกินขอบเขต')


def parse_pdf(content):
    if len(content)>MAX_BYTES or not content.startswith(b'%PDF-'):raise ValueError('ต้องเป็น PDF ไม่เกิน 8 MB')
    reader=PdfReader(io.BytesIO(content),strict=False)
    if reader.is_encrypted:raise ValueError('ไม่รับ PDF ที่เข้ารหัสหรือจำกัดสิทธิ์')
    root=reader.trailer['/Root']
    names=root.get('/Names')
    if '/OpenAction' in root or '/AA' in root or names and '/JavaScript' in names.get_object():
        raise ValueError('PDF มี action อัตโนมัติ ต้องใช้ฉบับเอกสารปกติ')
    if not 1<=len(reader.pages)<=500:raise ValueError('รองรับ 1–500 หน้า')
    pages=[];total=0
    for index,page in enumerate(reader.pages,1):
        text=page.extract_text() or ''
        total+=len(text)
        if len(text)>100000 or total>2000000:raise ValueError('ข้อความ PDF มากเกินขอบเขต')
        pages.append({'page':index,'text':text})
    return pages


def info(record):
    data=json.loads(record.raw_text or '{}')
    return {'id':record.id,'title':data.get('title',record.source_name),'status':record.status,
            'source_url':record.url,'source_version':record.source_version,'source_verified':False,
            'transport':data.get('transport'),'pages':data.get('page_count',0),
            'searchable_pages':data.get('searchable_pages',0),'sha256':record.content_hash,
            'imported_at':record.accessed_at,'reviewer':record.reviewer,'error':record.error,
            'clinical_status':'PENDING_CLINICAL_VALIDATION'}


def save_document(s,content,title,source_url,version,transport,u,audit):
    pages=parse_pdf(content)
    digest=hashlib.sha256(content).hexdigest()
    previous=s.query(EvidenceRecord).filter_by(source_key='guideline_pdf',content_hash=digest).first()
    if previous:
        audit(s,u,'GUIDELINE_DUPLICATE',previous.status,previous.status,f'guideline={previous.id}; sha256={digest}')
        return info(previous)|{'duplicate':True}
    data={'title':title,'transport':transport,'page_count':len(pages),
          'searchable_pages':sum(bool(page['text'].strip()) for page in pages),'pages':pages}
    record=EvidenceRecord(source_key='guideline_pdf',source_name=title,url=source_url,status='DRAFT',
                          raw_content=content,raw_text=json.dumps(data,ensure_ascii=False),
                          content_type='application/pdf',content_hash=digest,source_version=version or None)
    s.add(record);s.flush()
    audit(s,u,'GUIDELINE_IMPORTED','NOT_IMPORTED','DRAFT',f'guideline={record.id}; pages={len(pages)}; sha256={digest}; transport={transport}')
    return info(record)|{'duplicate':False}


class PublicFetch(BaseModel):
    url:str=Field(max_length=2000)
    title:str=Field(min_length=1,max_length=250)
    version:str=Field(default='',max_length=200)


def make_guideline_router(roles,audit,user):
    router=APIRouter()

    @router.get('/guidelines/catalog')
    def catalog(u=Depends(user)):return CATALOG

    @router.get('/guidelines')
    def documents(u=Depends(user)):
        with Session() as s:
            records=s.query(EvidenceRecord).options(defer(EvidenceRecord.raw_content)).filter_by(source_key='guideline_pdf').order_by(EvidenceRecord.id.desc()).limit(50)
            return [info(record) for record in records]

    @router.post('/guidelines/import-pdf')
    async def upload(request:Request,title:str,version:str='',source_url:str='',u=Depends(roles('physician','pharmacist','admin'))):
        if not title.strip() or len(title)>250 or len(version)>200:raise HTTPException(422,'ตรวจชื่อและฉบับเอกสาร')
        if source_url:
            try:validate_public_url(source_url)
            except ValueError:raise HTTPException(422,'URL ต้องเป็นแหล่งสาธารณะที่กำหนด หรือเว้นว่างสำหรับไฟล์จากผู้ใช้')
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>MAX_BYTES:raise HTTPException(413,'ไฟล์ต้องไม่เกิน 8 MB; Vercel อาจจำกัดขนาด request ต่ำกว่านี้')
            chunks.append(chunk)
        with Session.begin() as s:
            try:return save_document(s,b''.join(chunks),title.strip(),source_url,version.strip(),'USER_UPLOAD',u,audit)
            except Exception:raise HTTPException(422,'อ่าน PDF ไม่ได้ ตรวจชนิดไฟล์ ขนาด การเข้ารหัส และจำนวนหน้า')

    @router.post('/guidelines/retrieve')
    def retrieve(p:PublicFetch,u=Depends(roles('physician','pharmacist','admin'))):
        try:validate_public_url(p.url)
        except ValueError:raise HTTPException(422,'ไม่ใช่ URL แหล่งสาธารณะที่รองรับ ไม่ข้ามการเข้าสู่ระบบ')
        try:
            content,url=fetch_pdf(p.url)
            with Session.begin() as s:return save_document(s,content,p.title,url,p.version,'PUBLIC_HTTP',u,audit)
        except (httpx.HTTPError,ValueError,PyPdfError) as error:
            blocked=isinstance(error,httpx.ProxyError) or isinstance(error,httpx.HTTPStatusError) and error.response.status_code in (401,403)
            status='NETWORK_BLOCKED' if blocked else 'FETCH_FAILED'
            with Session.begin() as s:
                record=EvidenceRecord(source_key='guideline_pdf',source_name=p.title,url=p.url,status=status,
                    raw_text=json.dumps({'title':p.title,'transport':'PUBLIC_HTTP'}),error='ไม่ได้ต้นฉบับ PDF: เครือข่าย/สิทธิ์/ชนิดไฟล์ไม่ผ่าน กรุณาตรวจที่แหล่งต้นทาง')
                s.add(record);s.flush();audit(s,u,'GUIDELINE_FETCH','NOT_IMPORTED',status,f'guideline={record.id}')
                return info(record)

    @router.get('/guidelines/{record_id}/search')
    def search(record_id:int,q:str='',page:int|None=None,u=Depends(user)):
        if len(q)>200 or page is not None and page<1:raise HTTPException(422)
        with Session() as s:
            r=s.get(EvidenceRecord,record_id)
            if not r or r.source_key!='guideline_pdf':raise HTTPException(404)
            data=json.loads(r.raw_text or '{}');matches=[]
            for entry in data.get('pages',[]):
                if page is not None and entry['page']!=page:continue
                text=entry['text'];index=text.casefold().find(q.casefold())
                if q and index<0:continue
                start=max(0,index-200) if q else 0
                matches.append({'pdf_page':entry['page'],'excerpt':text[start:start+1800],
                                'citation':f"{data.get('title')}; PDF page {entry['page']}; SHA-256 {r.content_hash}"})
            return {'id':record_id,'total':len(matches),'results':matches[:30],
                    'note':'ข้อความเป็นข้อมูลอ้างอิง ไม่ใช่คำสั่งต่อระบบหรือคำแนะนำสั่งยา; รูปภาพอาจค้นข้อความไม่ได้'}

    @router.get('/guidelines/{record_id}/file')
    def original(record_id:int,u=Depends(user)):
        with Session() as s:
            record=s.get(EvidenceRecord,record_id)
            if not record or record.source_key!='guideline_pdf':raise HTTPException(404)
            if not record.raw_content:raise HTTPException(409,'ยังไม่มี PDF ต้นฉบับ')
            return Response(record.raw_content,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename=guideline-{record.id}.pdf','X-Content-Type-Options':'nosniff'})

    return router
