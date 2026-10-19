import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, DateTime, ForeignKey, LargeBinary, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
engine=create_engine(os.getenv('DATABASE_URL','sqlite:////tmp/renal-smart.db'), **({'connect_args':{'check_same_thread':False}} if os.getenv('DATABASE_URL','sqlite:').startswith('sqlite:') else {}))
Session=sessionmaker(engine)
class Base(DeclarativeBase): pass
class Patient(Base):
    __tablename__='patients'
    id:Mapped[str]=mapped_column(primary_key=True)
    source:Mapped[str]=mapped_column(Text)
class Drug(Base):
    __tablename__='drugs'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column(String(100),unique=True)
    evidence:Mapped[str]=mapped_column(Text,default='{}')
    status:Mapped[str]=mapped_column(default='PENDING_CLINICAL_VALIDATION')
    stock_status:Mapped[str]=mapped_column(default='IN_STOCK')
class Rule(Base):
    __tablename__='rules'
    id:Mapped[int]=mapped_column(primary_key=True)
    drug_id:Mapped[int]=mapped_column(ForeignKey('drugs.id'))
    version:Mapped[int]=mapped_column(default=1)
    status:Mapped[str]=mapped_column(default='DRAFT')
    specification:Mapped[str]=mapped_column(Text,default='{}')
    reviewer:Mapped[str|None]=mapped_column(nullable=True)
class Prescription(Base):
    __tablename__='prescriptions'
    id:Mapped[int]=mapped_column(primary_key=True)
    patient:Mapped[str]=mapped_column(default='SYN-001')
    department:Mapped[str]=mapped_column(default='อายุรกรรม')
    drug:Mapped[str]
    proposal:Mapped[str]=mapped_column(Text)
    decision:Mapped[str]
    source_snapshot:Mapped[str]=mapped_column(Text,default='{}')
    reason:Mapped[str]=mapped_column(Text,default='')
    status:Mapped[str]=mapped_column(default='SUBMITTED')
    finalized_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    stock_alternative_id:Mapped[int|None]=mapped_column(ForeignKey('stock_alternatives.id',use_alter=True,name='fk_prescription_stock_alternative'),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class StockAlternative(Base):
    __tablename__='stock_alternatives'
    id:Mapped[int]=mapped_column(primary_key=True)
    prescription_id:Mapped[int]=mapped_column(ForeignKey('prescriptions.id'))
    drug_id:Mapped[int]=mapped_column(ForeignKey('drugs.id'))
    proposed_by:Mapped[str]
    indication:Mapped[str]
    rationale:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(default='PROPOSED')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Audit(Base):
    __tablename__='audit'
    id:Mapped[int]=mapped_column(primary_key=True)
    user:Mapped[str]
    action:Mapped[str]
    previous:Mapped[str]
    new:Mapped[str]
    comments:Mapped[str]=mapped_column(Text,default='')
    record_id:Mapped[int|None]=mapped_column(nullable=True)
    timestamp:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class EvidenceRecord(Base):
    __tablename__='evidence_records'
    id:Mapped[int]=mapped_column(primary_key=True)
    source_key:Mapped[str]
    source_name:Mapped[str]
    url:Mapped[str]=mapped_column(Text)
    drug_id:Mapped[int|None]=mapped_column(ForeignKey('drugs.id'),nullable=True)
    status:Mapped[str]
    raw_text:Mapped[str|None]=mapped_column(Text,nullable=True)
    raw_content:Mapped[bytes|None]=mapped_column(LargeBinary,nullable=True)
    content_hash:Mapped[str|None]=mapped_column(nullable=True)
    content_type:Mapped[str|None]=mapped_column(nullable=True)
    source_version:Mapped[str|None]=mapped_column(nullable=True)
    reviewer:Mapped[str|None]=mapped_column(nullable=True)
    error:Mapped[str|None]=mapped_column(Text,nullable=True)
    accessed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
@event.listens_for(Audit,'before_update')
@event.listens_for(Audit,'before_delete')
def immutable(*args): raise ValueError('Audit records are append-only')
DRUGS=['Metformin','Sitagliptin','Gabapentin','Pregabalin','Allopurinol','Levofloxacin','Ciprofloxacin','Amoxicillin/Clavulanate','Enoxaparin','Famotidine']
def seed():
    with Session.begin() as s:
        import json
        if not s.get(Patient,'SYN-001'):
            s.add(Patient(id='SYN-001',source=json.dumps({'id':'SYN-001','name':'ผู้ป่วยจำลอง 001','age':65,'weight_kg':60,'sex':'female','scr':1.5,'egfr':38,'diagnosis':'เบาหวานชนิดที่ 2','allergies':[], 'medications':['Metformin'],'collected_at':datetime.now(timezone.utc).isoformat(),'verified':True,'stable':True,'dialysis':False,'actual_weight_appropriate':True,'unit':'mg/dL'},ensure_ascii=False)))
        for name in DRUGS:
            if not s.query(Drug).filter_by(name=name).first(): s.add(Drug(name=name,stock_status='OUT_OF_STOCK' if name=='Sitagliptin' else 'IN_STOCK'))

class FormularyItem(Base):
    __tablename__='formulary_items'
    code:Mapped[str]=mapped_column(String(100),primary_key=True)
    display_name:Mapped[str]=mapped_column(Text)
    generic_name:Mapped[str]=mapped_column(Text)
    strength:Mapped[str]=mapped_column(Text)
    unit:Mapped[str]=mapped_column(String(100))
    brand:Mapped[str]=mapped_column(Text)
    dosage_form:Mapped[str]=mapped_column(Text)
    source_stock_flag:Mapped[str]=mapped_column(String(100),default='')
    source_account_flag:Mapped[str]=mapped_column(String(100),default='')
    source_status_flag:Mapped[str]=mapped_column(String(100),default='')
    source_hash:Mapped[str]=mapped_column(String(64))
    source_row:Mapped[int]
    stock_status:Mapped[str]=mapped_column(String(30),default='UNKNOWN')
    stock_checked_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    present_in_latest_import:Mapped[bool]=mapped_column(default=True)
    imported_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
