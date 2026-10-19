"""Explicit XLS import: no macros/formula execution, prices or personal metadata retained."""
import hashlib
from datetime import datetime, timezone
from typing import Literal
import xlrd
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import or_
from .db import Session, FormularyItem

MAX_BYTES=8*1024*1024
COLUMNS={'รหัส':'code','ชื่อยา':'display_name','ชื่อสามัญ':'generic_name','ความแรง':'strength',
         'หน่วยนับ':'unit','ชื่อการค้า':'brand','Dosage Form':'dosage_form',
         'ยาหมด':'source_stock_flag','อยู่ในบัญชี':'source_account_flag','สถานะ':'source_status_flag'}
REQUIRED=('รหัส','ชื่อยา','ชื่อสามัญ','ความแรง','Dosage Form')


def parse_rows(headers,rows,source_hash):
    headers=[str(value).strip() for value in headers]
    if any(headers.count(key)!=1 for key in REQUIRED):
        raise ValueError('ต้องมีหัวตาราง รหัส ชื่อยา ชื่อสามัญ ความแรง และ Dosage Form อย่างละหนึ่งช่อง')
    indexes={field:headers.index(label) for label,field in COLUMNS.items() if label in headers}
    result=[];seen=set()
    for row_number,row in enumerate(rows,2):
        if not any(str(value).strip() for value in row):continue
        item={field:str(row[index]).strip() if index<len(row) else '' for field,index in indexes.items()}
        if not item['code'] or len(item['code'])>100 or not item['display_name']:
            raise ValueError(f'รหัสหรือชื่อยาไม่ครบที่แถว {row_number}')
        if item['code'] in seen:raise ValueError(f'รหัสยาซ้ำในไฟล์ที่แถว {row_number}')
        if any(len(value)>2000 for value in item.values()):raise ValueError('ข้อความในช่องยาวเกินขอบเขต')
        seen.add(item['code'])
        for field in COLUMNS.values():item.setdefault(field,'')
        # A source flag is historical/uninterpreted; blank never implies availability.
        result.append(item|{'source_hash':source_hash,'source_row':row_number})
    if not result or len(result)>10000:raise ValueError('จำนวนรายการต้องอยู่ระหว่าง 1–10000')
    return result


def parse_xls(content):
    if len(content)>MAX_BYTES:raise ValueError('ไฟล์ต้องไม่เกิน 8 MB')
    if not content.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        raise ValueError('รองรับ Excel .xls แบบ BIFF เท่านั้น ไม่รัน macro หรือสูตร')
    book=None
    try:
        book=xlrd.open_workbook(file_contents=content,on_demand=True)
        candidates=[]
        for sheet in book.sheets():
            if sheet.nrows and all(str(value).strip() in [str(v).strip() for v in sheet.row_values(0)] for value in REQUIRED):
                candidates.append(sheet)
        if len(candidates)!=1:raise ValueError('ต้องพบ sheet บัญชียาที่มีหัวตารางครบเพียงหนึ่ง sheet')
        sheet=candidates[0]
        if sheet.nrows>10001:raise ValueError('จำนวนรายการมากเกิน 10000')
        return parse_rows(sheet.row_values(0),(sheet.row_values(r) for r in range(1,sheet.nrows)),hashlib.sha256(content).hexdigest())
    except xlrd.XLRDError as exc:
        raise ValueError('อ่านโครงสร้าง XLS ไม่ได้') from exc
    finally:
        if book:book.release_resources()


def import_items(session,items):
    now=datetime.now(timezone.utc)
    session.query(FormularyItem).update({'present_in_latest_import':False})
    existing={item.code:item for item in session.query(FormularyItem).all()}
    for data in items:
        item=existing.get(data['code'])
        if item is None:
            item=FormularyItem(code=data['code'],stock_status='UNKNOWN');session.add(item)
        elif item.source_hash!=data['source_hash']:
            # A new export is not proof that a past manual stock check is still current.
            item.stock_status='UNKNOWN';item.stock_checked_at=None
        for key,value in data.items():setattr(item,key,value)
        item.present_in_latest_import=True;item.imported_at=now
    return {'imported':len(items),'source_hash':items[0]['source_hash'],
            'note':'รายการในไฟล์ไม่ยืนยันสถานะใช้ในบัญชีหรือยอดคงเหลือ และไม่ใช่กฎขนาดยา'}


def item_view(item):
    return {column.name:getattr(item,column.name) for column in FormularyItem.__table__.columns}


class StockCheck(BaseModel):
    status:Literal['UNKNOWN','IN_STOCK','OUT_OF_STOCK']


def make_formulary_router(roles,audit):
    router=APIRouter()

    @router.get('/formulary')
    def list_items(q:str='',offset:int=0,limit:int=50,u=Depends(roles('physician','pharmacist','admin'))):
        if offset<0 or not 1<=limit<=100 or len(q)>200:raise HTTPException(422,'ช่วงค้นหาไม่ถูกต้อง')
        with Session() as s:
            base=s.query(FormularyItem).filter_by(present_in_latest_import=True)
            total=base.count()
            if q.strip():
                base=base.filter(or_(*[column.contains(q.strip(),autoescape=True) for column in
                    (FormularyItem.code,FormularyItem.display_name,FormularyItem.generic_name,FormularyItem.brand)]))
            return {'total':total,'matched':base.count(),'items':[item_view(item) for item in base.order_by(FormularyItem.display_name).offset(offset).limit(limit)]}

    @router.post('/formulary/import-xls')
    async def upload(request:Request,u=Depends(roles('pharmacist','admin'))):
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>MAX_BYTES:raise HTTPException(413,'ไฟล์ต้องไม่เกิน 8 MB')
            chunks.append(chunk)
        try:items=parse_xls(b''.join(chunks))
        except Exception:
            # Do not echo parser exceptions that may contain workbook contents.
            raise HTTPException(422,'นำเข้าไม่ได้: ต้องเป็น XLS ไม่เกิน 8 MB หัวตารางครบ รหัสไม่ซ้ำ และ 1–10000 รายการ')
        with Session.begin() as s:
            result=import_items(s,items)
            audit(s,u,'FORMULARY_IMPORTED','PREVIOUS_CATALOG','IMPORTED',f"rows={result['imported']}; sha256={result['source_hash']}")
            return result

    @router.post('/formulary/{code}/stock')
    def stock_check(code:str,p:StockCheck,u=Depends(roles('pharmacist','admin'))):
        with Session.begin() as s:
            item=s.get(FormularyItem,code)
            if not item or not item.present_in_latest_import:raise HTTPException(404)
            previous=item.stock_status;item.stock_status=p.status
            item.stock_checked_at=datetime.now(timezone.utc)
            audit(s,u,'FORMULARY_STOCK_CHECK',previous,p.status,code)
            return item_view(item)

    return router
