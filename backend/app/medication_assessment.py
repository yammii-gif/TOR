"""Separate an approved patient decision from unapproved document findings."""
import json
from pathlib import Path
from .clinical import calculate

DOCUMENT = json.loads((Path(__file__).parent / 'knowledge' / 'thai_ckd_2022.json').read_text())


def document_metadata():
    return {key: value for key, value in DOCUMENT.items() if key != 'findings'}


def assess_medication(patient, drug, indication):
    calculation = calculate(patient)
    ready = calculation['status'] == 'SIMULATION'
    reason = calculation.get('reason') if not ready else 'ยังไม่มีกฎยาฉบับ ACTIVE ที่ผ่านการรับรองและครอบคลุมบริบทนี้'
    if not drug.strip() or not indication or not indication.strip():
        reason = 'ระบุชื่อยาและข้อบ่งใช้ก่อนประเมิน ไม่อนุมานว่าทุกยาใช้รักษาข้อบ่งใช้เดียวกัน'
        ready = False
    # No clinical rule is activated in this release. A document match never changes the verdict.
    findings = []
    if ready and drug.strip().casefold() == 'metformin' and indication.strip().casefold() in ('type 2 diabetes', 'เบาหวานชนิดที่ 2'):
        finding = DOCUMENT['findings'][0]
        band = None
        # Use the explicitly entered reported eGFR, not CrCl or a rounded calculated eGFR.
        if patient.egfr is not None:
            band = next(b for b in finding['bands'] if patient.egfr >= b['lower_inclusive'] and
                        (b['upper_exclusive'] is None or patient.egfr < b['upper_exclusive']))
        findings.append({key: value for key, value in finding.items() if key != 'bands'} | {
            'source': document_metadata(), 'matched_band': band,
            'comparison_value': patient.egfr,
            'comparison_basis': 'eGFR จากแล็บที่กรอก (ต้องยืนยันต้นทาง)',
            'actionable': False,
        })
    return {
        'status': 'PENDING_CLINICAL_VALIDATION' if ready else (calculation['status'] if calculation['status'] != 'SIMULATION' else 'CLINICAL_REVIEW_REQUIRED'),
        'decision': {'code': 'REVIEW_REQUIRED', 'label': 'ยังสรุปไม่ได้ — ต้องทบทวน',
                     'reason': reason, 'scope': 'ความเหมาะสมของยาตามการทำงานของไต',
                     'actionable': False, 'dose': None},
        'dose': None, 'alternatives': [],
        'alternatives_status': 'NO_VALIDATED_ALTERNATIVE — CLINICAL REVIEW REQUIRED',
        'alternatives_reason': 'ยังไม่มีกฎยาทางเลือกที่รับรองตามข้อบ่งใช้ ภูมิแพ้ โรคร่วม ยาร่วม และข้อมูลไต ไม่ถือว่ายาในคลังใช้แทนกันได้',
        'calculation': calculation, 'document_findings': findings,
    }
