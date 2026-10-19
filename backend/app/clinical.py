"""Research calculations only; no activated clinical dose rules."""
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class RenalInput(BaseModel):
    age: int = Field(ge=18, le=120)
    weight_kg: float = Field(gt=0, le=400)
    sex: str
    scr: float = Field(gt=0, le=3000)
    unit: str = 'mg/dL'
    collected_at: datetime
    verified: bool = False
    stable: bool = True
    dialysis: bool | None = False
    actual_weight_appropriate: bool = False
    egfr: float | None = Field(default=None, ge=0, le=250)

def calculate(p: RenalInput):
    if p.sex not in ('male', 'female') or p.unit not in ('mg/dL', 'µmol/L'):
        return {'status': 'VERIFICATION_REQUIRED', 'reason': 'ตรวจสอบเพศที่ใช้ในสูตรและหน่วย SCr'}
    age_hours = (datetime.now(timezone.utc)-p.collected_at.replace(tzinfo=p.collected_at.tzinfo or timezone.utc)).total_seconds()/3600
    if not p.verified or age_hours < 0 or age_hours > 48:
        return {'status': 'VERIFICATION_REQUIRED', 'reason': 'ข้อมูลยังไม่ยืนยันหรือผลแล็บเกิน 48 ชั่วโมง (เกณฑ์เดโม)'}
    if not p.stable or p.dialysis is not False or not p.actual_weight_appropriate:
        return {'status': 'CLINICAL_REVIEW_REQUIRED', 'reason': 'ต้องทบทวนภาวะไต การฟอกไต หรือการเลือกน้ำหนัก'}
    scr = p.scr/88.4 if p.unit == 'µmol/L' else p.scr
    crcl = (140-p.age)*p.weight_kg/(72*scr)*(0.85 if p.sex == 'female' else 1)
    return {'status': 'SIMULATION', 'crcl': round(crcl,2), 'unit': 'mL/min', 'egfr': p.egfr,
            'formula': '(140 − age) × weight / (72 × SCr) × (0.85 if female)',
            'weight_basis': 'actual weight, explicitly confirmed appropriate',
            'source': 'Cockcroft DW, Gault MH. Nephron. 1976;16:31–41. doi:10.1159/000180580',
            'warning': 'ค่าประมาณสำหรับงานวิจัย; eGFR และ CrCl ใช้แทนกันไม่ได้'}

def evaluate(patient, rule=None, indication=None):
    result=calculate(patient)
    if result['status'] != 'SIMULATION': return result
    if not indication: return {'status':'CLINICAL_REVIEW_REQUIRED','dose':None}
    # No clinician-approved rules shipped. Never infer dosing from a calculation.
    return {'status':'PENDING_CLINICAL_VALIDATION','dose':None,
            'alternatives_status':'NO_VALIDATED_ALTERNATIVE — CLINICAL REVIEW REQUIRED','calculation':result}
