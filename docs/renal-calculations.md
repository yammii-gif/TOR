# ข้อกำหนดการคำนวณไตในต้นแบบ

สถานะ: implemented published equations / **PENDING CLINICAL VALIDATION**. ไม่มีการรับรองจากสถาบันหรือกฎขนาดยาที่ active ข้อมูลในเว็บยังเป็น SYNTHETIC DATA

## Inputs และการกั้นผล

ผู้ใหญ่อายุ 18–120 ปี, sex parameter male/female ตามสูตร, SCr และหน่วย, น้ำหนัก kg สำหรับ CrCl, เวลาเก็บเลือด, การยืนยันข้อมูล, renal stability และ dialysis status. ใช้ actual weight เฉพาะผู้ใช้ยืนยันว่าเหมาะสม การเลือกน้ำหนักใน obesity/edema/underweight ต้องทบทวนแยก ไม่เลือกให้โดยอัตโนมัติ

- SCr µmol/L ÷ 88.4 = mg/dL ก่อนใช้ทั้งสองสูตร
- eGFR ที่ผู้ใช้กรอกจากแล็บเป็น reported value เท่านั้น ไม่ถูกใช้เป็นคำตอบคำนวณ
- หยุดการแสดงค่าคำนวณเมื่อข้อมูลไม่ยืนยัน, แล็บเกิน 48 ชั่วโมง/เป็นอนาคต, renal function ไม่คงที่, dialysis details ไม่ทราบ/มีการฟอกไต หรือการเลือกน้ำหนักยังไม่ยืนยัน
- 48 ชั่วโมงเป็นนโยบายเดโม ต้องให้สถาบันตรวจสอบตาม clinical context ก่อนใช้จริง
- ป้องกัน input SCr ≤ 0, missing/NaN/infinite และ numeric underflow/overflow

## Cockcroft–Gault

CrCl = (140 − age) × weight_kg / (72 × SCr_mg_dL) × (0.85 สำหรับ female, 1 สำหรับ male), หน่วย **mL/min**.

Cockcroft DW, Gault MH. Nephron. 1976;16:31–41. https://doi.org/10.1159/000180580

## CKD-EPI 2021 creatinine, race-free

eGFR = 142 × min(SCr/κ, 1)^α × max(SCr/κ, 1)^−1.200 × 0.9938^age × (1.012 สำหรับ female, 1 สำหรับ male)

- female: κ = 0.7, α = −0.241
- male: κ = 0.9, α = −0.302
- หน่วย **mL/min/1.73m²**, ใช้ในผู้ใหญ่ ไม่มี race coefficient
- ไม่ใช่ measured GFR และไม่ใช้แทน CrCl หรือ absolute unindexed GFR โดยอัตโนมัติ

Inker LA et al. New Creatinine- and Cystatin C–Based Equations to Estimate GFR without Race. N Engl J Med. 2021;385:1737–1749. https://doi.org/10.1056/NEJMoa2102953

## กรณีตรวจสอบ

หญิงอายุ 65 ปี น้ำหนัก 60 kg, SCr 1.5 mg/dL: CrCl **35.42 mL/min**, CKD-EPI 2021 eGFR **38.43 mL/min/1.73m²**. SCr 132.6 µmol/L ต้องได้ค่าเดียวกัน การกรอก reported eGFR 99 หรือไม่กรอก ต้องไม่เปลี่ยนผลคำนวณ

Tests ใช้ reference fixtures จากการประเมิน specification ด้วย Decimal precision 40 digits แยกจาก implementation ตรวจทั้งสองเพศ ค่า SCr ต่ำกว่า/เท่ากับ/สูงกว่า κ, อายุ 18/90, การแปลงหน่วย และ unsafe/missing inputs. ผลผ่าน automated tests ไม่ใช่การอนุมัติใช้กับผู้ป่วยจริง

UI แสดงสองค่าแยกหน่วย แสดง reported lab value แยกต่างหาก และล้างผลเก่าทันทีเมื่อแก้ input ต้องกดคำนวณใหม่ มี input เวลาแล็บและ dialysis status สำหรับตรวจสอบการกั้นผล
