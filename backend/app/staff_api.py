from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from typing import Literal
from .db import Session,StaffUser
from .identity import create_account,change_account,account_view
from .runtime import production

Role=Literal['physician','pharmacist','admin','researcher']
class CreateStaff(BaseModel):
    username:str=Field(min_length=3,max_length=64)
    password:str=Field(min_length=12,max_length=256)
    role:Role
class ChangeStaff(BaseModel):
    role:Role|None=None
    enabled:bool|None=None
    password:str|None=Field(default=None,min_length=12,max_length=256)


def make_staff_router(roles):
    router=APIRouter()
    def configured():
        if not production():raise HTTPException(409,'บัญชีรายบุคคลใช้ในโหมดproduction; เดโมไม่สร้างบัญชีผู้ใช้จริง')

    @router.get('/admin/users')
    def accounts(u=Depends(roles('admin'))):
        configured()
        with Session() as s:return [account_view(a) for a in s.query(StaffUser).order_by(StaffUser.username)]

    @router.post('/admin/users')
    def create(p:CreateStaff,u=Depends(roles('admin'))):
        configured()
        with Session.begin() as s:
            try:return create_account(s,p.username,p.password,p.role,u['name'])
            except ValueError:raise HTTPException(409,'สร้างบัญชีไม่ได้ ตรวจชื่อบัญชีซ้ำ รูปแบบชื่อ และความยาวรหัสผ่าน')

    @router.post('/admin/users/{account_id}')
    def change(account_id:int,p:ChangeStaff,u=Depends(roles('admin'))):
        configured()
        with Session.begin() as s:
            try:return change_account(s,account_id,u['name'],p.role,p.enabled,p.password)
            except ValueError:raise HTTPException(409,'เปลี่ยนบัญชีไม่ได้ ตรวจข้อมูลและต้องเหลือผู้ดูแลที่เปิดใช้งานอย่างน้อยหนึ่งบัญชี')

    return router
