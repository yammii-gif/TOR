# Desktop Agent — simulation and deployment requirements

`python desktop/simulator.py --ocr` สร้างภาพ HOSxP-like สังเคราะห์ใน memory แล้วส่งเข้า Tesseract ในเครื่อง อ่าน HN อายุ น้ำหนัก sex SCr eGFR เวลาแล็บ diagnosis medication dose/frequency และรายงาน confidence ขนาดยาในภาพเป็น UNVERIFIED โดยเจตนา ไม่เก็บภาพลงดิสก์

Simulator ต้อง start ก่อน process, pause/stop หยุดการประมวลผล และ pause เมื่อเปลี่ยน patient identity; interval default 2.5s ไม่มี background screen monitoring จริง

## Communication contract

`POST /agent/capture` ใช้ physician session cookie ที่ยืนยันตัวตนแล้ว ส่ง JSON:

```json
{"patient_id":"SYN-001","expected_patient_id":"SYN-001","confidence":0.99,"fields":{"scr":1.5,"unit":"mg/dL","collected_at":"2026-10-19T00:00:00Z"},"monitoring":true}
```

API นี้เป็น synthetic demo transport เท่านั้น ไม่รับภาพจริง ไม่ยืนยันข้อมูลผู้ป่วยโดยอัตโนมัติ และคืน `clinical_recommendations_enabled: false` เสมอ Browser Auto Lab ส่ง payload จำลอง ไม่ได้เรียก OCR ใน Windows

## Before Windows deployment

ต้องพัฒนา signed Windows agent และ hospital-managed enrollment/authentication ก่อนใช้งาน เลือก process/executable/window title ที่สถาบัน allowlist ตรวจ HWND ทุกเฟรม จำกัดเฉพาะ approved region ห้ามจับทั้ง desktop ต้องมีสถานะ monitoring ที่เห็นชัดและ pause/stop พร้อมล้าง buffer ภาพ ผู้ใช้เริ่มเองทุกครั้ง (2–3 วินาที) ไม่ใช้ credentials ร่วมกับ prototype demo login

OCR confidence threshold เป็นเพียงตัวอย่าง ต้องประเมินระดับ field กับ ground truth ตรวจ decimal/unit/time/sex/HN วนซ้ำสองเฟรมเมื่อ identity เปลี่ยน quarantine และขอคนยืนยัน ห้ามจับภาพคนไข้จริงจนผ่าน consent, PDPA, security review และ validation ของ HOSxP v4 รุ่นที่ติดตั้ง

ควรใช้ read-only structured HOSxP/LIS adapter ที่ได้รับอนุญาตก่อน OCR ไม่มี claim ว่าทดสอบ HOSxP จริงแล้ว

## อ่านแถบแล็บในเครื่อง (ไม่อัปโหลด)

รัน `python desktop/lab_region.py` บนเครื่องที่ติดตั้ง Python, Pillow, pytesseract, Tesseract และ Tkinter แล้วเลือก PNG เฉพาะแถบแล็บ ภาพเปิดใน memory และไม่มีการบันทึกซ้ำหรือส่งเครือข่าย ผลแสดงเฉพาะหน้าต่าง local และล้างได้ ปิดหน้าต่างเพื่อล้าง memory ของโปรเซส

Profile `hosxp-lab-strip-1395x224-v1` เก็บเฉพาะพิกัดช่อง BW, Height, Cr, eGFR จากรูปแบบที่ผู้ใช้ระบุ ไม่เก็บภาพหรือค่าผู้ป่วยใน repository ขนาดและตำแหน่งต้องตรง 1395×224; หาก resize, เปลี่ยน DPI หรือ layout ต้องปรับ profile และตรวจรับใหม่ ความมั่นใจ OCR ไม่ได้ยืนยันว่าช่องที่อ่านถูกคนหรือถูกแล็บ ตัวอ่านนี้ยังไม่จับหน้าต่าง Windows อัตโนมัติและยังไม่ผ่านการทดสอบกับ HOSxP จริง

ไม่อนุมานหน่วย Cr, หน่วย eGFR, HN, อายุ, sex หรือเวลาเก็บแล็บจากตัวเลขในแถบนี้ ไม่สลับ BSA/RR โดยเดา และไม่ส่งค่าจากตัวอ่านไป calculator หรือเว็บสาธารณะอัตโนมัติ ทุกผลเป็น `VERIFICATION_REQUIRED` จนตรวจจับคู่ผู้ป่วย หน่วย และเวลาจากแหล่งต้นทางที่เชื่อถือได้ ตัวอย่างทดสอบเป็นค่าที่สร้างใหม่ทั้งหมด
