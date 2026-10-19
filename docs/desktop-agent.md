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
