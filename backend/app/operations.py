"""Non-sensitive operational health. Availability is separate from clinical approval."""
from sqlalchemy import text
from fastapi import HTTPException
from .db import Session,StaffUser
from .runtime import production,expected_schema


def readiness():
    checks={'database':False,'schema':False,'administrator':False,'least_privilege':False}
    try:
        with Session() as s:
            s.execute(text('SELECT 1'));checks['database']=True
            if production():
                revision=s.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
                checks['schema']=revision==expected_schema()
                checks['administrator']=s.query(StaffUser).filter_by(role='admin',enabled=True).first() is not None
                checks['least_privilege']=not s.execute(text("SELECT has_table_privilege(current_user,'audit','UPDATE') OR has_table_privilege(current_user,'audit','DELETE') OR has_table_privilege(current_user,'audit','TRUNCATE') OR has_schema_privilege(current_user,'public','CREATE')")).scalar_one()
            else:checks['schema']=True;checks['administrator']=True;checks['least_privilege']=True
    except Exception:
        raise HTTPException(503,'ฐานข้อมูลหรือschemaยังไม่พร้อม กรุณาตรวจบริการและmigrations') from None
    if not all(checks.values()):raise HTTPException(503,'ระบบยังไม่พร้อม ตรวจmigrations บัญชีผู้ดูแล และสิทธิ์runtimeที่ต้องไม่เป็นowner')
    return {'status':'ok','mode':'SYNTHETIC DATA','app_version':'2.3','hosting_mode':'production' if production() else 'development',
            'clinical_ready':False,'checks':checks}
