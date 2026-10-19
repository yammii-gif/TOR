# เส้นทางเปิดใช้งานในห้องตรวจ

เป้าหมายที่ผู้ใช้ปรับล่าสุดคือการใช้งานหน้างานจริง ไม่ใช่งานวิจัยเพียงอย่างเดียว แต่การเปลี่ยนเป้าหมายไม่ทำให้กฎยา บัญชีร่วม หรือข้อมูล OCR ผ่านการตรวจรับโดยอัตโนมัติ รุ่นปัจจุบันจึงยังป้องกันข้อมูลจริงใน API และปิด actionable drug dosing ไว้

## Workflow ที่ทำงานแล้ว

- แพทย์กรอกข้อเสนอยาและยืนยันเองได้ทันที ถ้ายังไม่ถูกระบุว่ายาหมด สถานะ `PHYSICIAN_FINALIZED` ไม่ต้องผ่านการอนุมัติซ้ำโดยเภสัชกร
- หากยาขาดคลัง สถานะ `WAITING_STOCK_ALTERNATIVE`; เภสัชกรเสนอจากรายการ `IN_STOCK` พร้อมข้อบ่งใช้/เหตุผล แพทย์ตรวจและเลือกหรือปฏิเสธ การเลือกต้องกรอกวิธีใช้เองและบันทึกเหตุผล
- การมีในคลังไม่ได้ยืนยันความเทียบเท่าทางการรักษา ระบบไม่สร้างขนาดยาหรืออ้างว่าสองยาใช้แทนกันได้
- การยืนยันนี้เป็นบันทึกภายในโปรแกรม ไม่ใช่การส่งใบสั่งยาเข้า HOSxP การประเมินที่ข้อมูลไม่พร้อมต้องให้แพทย์แก้ข้อมูลหรือบันทึก manual override

## งานที่ต้องผ่านก่อนรับข้อมูลจริง

| งาน | สถานะปัจจุบัน | สิ่งที่ต้องตรวจรับ |
| --- | --- | --- |
| บัญชีรายบุคคล | มีเฉพาะ demo password + role selector | Hospital SSO/OIDC, staff roles, revocation, access review |
| ฐานข้อมูล | Postgres รองรับ migrations; Vercel เดโมใช้ /tmp SQLite | ฐานข้อมูลถาวรของหน่วยงาน backup/restore, encryption, retention |
| HOSxP/LIS | simulator + local PNG ROI reader | authorized read-only adapter ก่อน OCR, patient/encounter mapping, units, timestamps |
| Windows OCR | ไม่มี live window capture ที่ตรวจรับแล้ว | signed agent, allowlisted process/region, explicit start/pause/stop, field accuracy, identity-change quarantine |
| คำนวณ | CG และ CKD-EPI2021 พร้อม automated tests | institution-reviewed specs; AKI/dialysis/body size/weight context; independent reference comparison |
| กฎยา | ไม่มี approved active dose rules | เภสัชกร/แพทย์ทบทวนหลักฐานและ version, indication, measure, thresholds, contraindications, interactions และ monitoring |
| ความปลอดภัย | session cookie + role checks + ORM audit | threat model, penetration testing, DB access policy, tamper-resistant audit, PDPA/data governance |
| คลังกายภาพ | บัญชีจากไฟล์827ผลิตภัณฑ์พร้อม UNKNOWN / ผลตรวจ manual | authorized formulary/stock integration, freshness, race/conflict policy |

อย่าส่ง HN หรือภาพผู้ป่วยจริงเข้าบริการ Vercel เดโมนี้ระหว่างรอรายการข้างต้น การติดตั้งจริงควรอยู่ในเครือข่าย/hosting ที่หน่วยงานอนุมัติ พร้อม HTTPS และฐานข้อมูลถาวร สิทธิ์ read-only HOSxP/LIS ต้องแยกจากสิทธิ์เขียนใบสั่งยา

## UpToDate และข้อมูลอ้างอิง

หน้าค้นหาสาธารณะ `https://www.uptodate.com/contents/search` แยกจากบทความเต็มและ Lexidrug ที่ต้องมีวิธีเชื่อมต่อที่ได้รับอนุญาต ไม่มีการข้ามสิทธิ์หรือส่ง cookie จาก browser ของผู้ใช้

ตัวค้นหาบันทึกต้นฉบับ เฉพาะเมื่อ HTTP สำเร็จและได้ bytes จริง ไม่ถือว่า search snippet เป็น prescribing rule และไม่เปิดใช้งานกฎใหม่อัตโนมัติ ขณะพัฒนาครั้งนี้ proxy ของ cloud ตอบ CONNECT 403 ต่อ URL ค้นหาที่ผู้ใช้ให้มา จึงยังไม่มีบทความปัจจุบันถูกนำเข้า การเปิดลิงก์ใน browser ของโรงพยาบาลอาจได้ผลต่างกัน

สำหรับภาพแถบแล็บ ต้องระบุตำแหน่ง HN/encounter อายุ sex หน่วย Cr/หน่วย eGFR และเวลาเก็บแล็บจากแหล่งที่ได้รับอนุญาตเพิ่มเติม ตัวอ่านไม่สร้างข้อมูลเหล่านี้ขึ้นเอง เก็บใน repo เพียงตำแหน่งช่อง ไม่เก็บภาพผู้ป่วย
