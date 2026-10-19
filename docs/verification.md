# ผลการตรวจสอบใน cloud instance

วันที่ 19 ตุลาคม 2026 — ใช้ข้อมูลสังเคราะห์เท่านั้น

- Backend: 23 tests passed (สูตร/หน่วย/แล็บเก่าและอนาคต/ข้อมูลขาด/unstable renal/dialysis/weight confirmation/no validated alternative/OCR wrong-patient and confidence/override reason/role checks/rule versions and activation block/pharmacist rejection/snapshot/audit)
- Frontend: ESLint, TypeScript และ Next.js production build ผ่าน
- Playwright: 1 end-to-end test ผ่านด้วย system Chromium: login physician → คำนวณ CrCl → ส่งข้อเสนอ → logout → login pharmacist → reject → ตรวจ audit
- SQLite: Alembic migrations ผ่าน; repeatable seed ผ่านผ่าน install script
- PostgreSQL 16: Docker database healthy, Alembic migrations และ seed สองครั้งผ่าน
- OCR: สร้างภาพสังเคราะห์ใน memory และ Tesseract อ่าน HN/age/weight/sex/SCr/eGFR/lab date/diagnosis/medication ได้; minimum word confidence 0.80 จึงคง VERIFICATION_REQUIRED ไม่อ้างว่าเป็นการวัด accuracy
- Runtime: API health ตอบ ok พร้อม SYNTHETIC DATA; frontend HTTP 200
- ./scripts/install.sh ผ่านครบ; ./scripts/start-demo.sh เริ่มบริการได้ และ browser workflow ผ่านหลัง restart
- Docker Compose config ถูกต้องและ database service ทำงาน แต่ image build ของแอปติด DNS ของ proxy ภายใน builder (ลอง default และ host build network + standard proxy args แล้ว) ไม่ได้ปิด TLS/checksum verification เพื่อแก้
- DailyMed: CONNECT proxy 403; ไม่ได้ดึงฉลากหรือข้อมูลยาที่ตรวจสอบแล้ว บันทึก dailymed.nlm.nih.gov ใน configuration draft แต่ยังไม่อ้างว่ามีผลกับ runtime หรือเผยแพร่แล้ว

ไม่ได้ทดสอบ real HOSxP, Windows capture, production auth, approved clinical dosing หรือ fresh-task snapshot restoration. ดู README และ clinical-validation checklist สำหรับข้อจำกัดทั้งหมด

## การเริ่มเว็บเพื่อทดลองใช้งาน

- Restart frontend/backend ผ่าน `scripts/start-demo.sh` แล้ว; frontend HTTP 200 และ `/api/health` คืน SYNTHETIC DATA
- เพิ่ม same-origin API proxy พร้อม forwarded HttpOnly login/logout cookie และ Docker backend hostname config
- Environment นี้ไม่มี Preview/port-forwarding tool และไม่มี desktop display ที่ผู้ใช้เปิดใช้งานได้ จึงยังไม่มี public URL สำหรับทดลองจากนอก cloud; ไม่อ้างว่าลิงก์ localhost เป็นลิงก์สาธารณะ

## Render deployment preparation

เพิ่ม `render.yaml` และ scripts สำหรับ native Python web service ที่รัน Next.js/FastAPI ในพอร์ตภายนอกเดียว ทดสอบ `build-online.sh` ผ่านครบ และ `start-online.sh` ผ่านด้วยพอร์ต web/backend แยกจากเดโมเดิม SQLite ใหม่ถูก migrate/seed อัตโนมัติ, `/api/health` ตอบ SYNTHETIC DATA, Playwright 2 tests ผ่านผ่าน startup นี้ และ backend 23 tests ผ่าน ไม่มีการ deploy เข้าบัญชี Render จริง เนื่องจากไม่ได้เชื่อมบัญชี/credential; จึงยังไม่มี public service URL และยังไม่ได้ตรวจ cold start บน Render

## Vercel serverless preparation

Backend 29 tests ผ่าน รวม HMAC session ข้าม memory stores, tampered/expired tokens และ missing session secret. Frontend lint/typecheck/normal build และ static export ผ่าน. Browser tests 2 รายการผ่านบน static export + Python adapter ใน instance เดียว (แพทย์ส่งข้อเสนอ → เภสัชกร reject → audit และ cookie login/logout). Multi-instance storage consistency ไม่ได้รับการรับรอง; UI มีคำเตือน ephemeral serverless simulation. ข้อมูลไม่คงทนเหมือน shared database

การเผยแพร่ environment สำเร็จและค่าที่อ่านได้มี vercel.com/api.vercel.com แต่ runtime ยังตอบ CONNECT proxy 403 ทั้งสองโดเมน จึงยังไม่สามารถทำ CLI login/deploy จริง และยังไม่มี Vercel deployment URL ที่ตรวจสอบแล้ว ไม่มีการขอให้เพิ่มโดเมนเดิมซ้ำหรือส่ง credentials ผ่านแชต

## การปรับ workflow ห้องตรวจและ evidence infrastructure ล่าสุด

- Backend 74 tests ผ่าน: CG/CKD-EPI2021, unit conversion, lab validity, missing data, renal guards, rule permissions/versioning, physician immediate finalization, stock exception alternatives/decline/race check, legacy pharmacist rejection, roles/audit, licensed/public evidence separation, checksum/conflict และ local ROI safety gates
- Frontend lint, typecheck, production build และ Vercel static export ผ่าน
- Playwright 5 tests ผ่านบน static export + Python adapter: physician immediate finalization, same-origin session, renal recalc/stale result, stock exception→pharmacist proposal→physician choice, licensed-source status
- SQLite migration 002→004 ทดสอบกับฐานข้อมูล schema เก่าและรักษารายการเดิม; PostgreSQL16 upgrade head + seed ผ่าน
- Local ROI tests ใช้ภาพเปล่า/reader fixture และตัวเลขสังเคราะห์เท่านั้น ไม่ใช่การวัดความแม่นยำจากภาพผู้ป่วยจริง ไม่มีการทดสอบ Windows live capture
- URL UpToDate Public Search ที่ผู้ใช้ระบุถูก proxy ตอบ CONNECT403 ไม่มีบทความปัจจุบันถูกดึงสำเร็จ ไม่ถือว่าเป็นการตอบให้ล็อกอินจาก UpToDate เอง แหล่ง public เพิ่มใน configuration draft; draft ต้อง publish ก่อนจึงจะมีผลและยังไม่รับประกัน runtime egress
- ยังไม่มี production identity, approved active drug rules, real HOSxP/LIS integration หรือการตรวจรับ deployment Vercel จากภายนอก

## เอกสาร CKD และรายการยาโรงพยาบาล

- Backend 96 tests ผ่าน รวมการแยก unapproved document finding จาก patient verdict, ขอบเขต eGFR 29.999/30/44.999/45/59.999/60, missing indication/renal context และการไม่ใช้ CrCl แทน eGFR
- Browser 6 tests ผ่าน รวมผลประเมินอัตโนมัติเมื่อเปลี่ยนยา/แล็บ และการล้างผลเก่า โดยยังไม่เปิดคำตัดสินที่ไม่ได้รับรอง
- XLS ต้นฉบับจากผู้ใช้ parse/import ผ่าน API local จริง 827 รายการ รหัสไม่ซ้ำ ช่องสถานะว่างจึง stock UNKNOWN ทุกตัว ไม่เก็บราคา metadata ผู้จัดทำหรือไฟล์ดิบในฐานข้อมูล/รีโป
- Formulary tests ครอบคลุมแยกผลิตภัณฑ์ ไม่อนุมาน stock จากช่องว่าง นำเข้าซ้ำ ปฏิเสธรหัสซ้ำ/ไฟล์ผิด role/audit และ reset stock เมื่อ source hash เปลี่ยน
- SQLite schemaเก่า002→005 รักษาข้อมูลเดิม; PostgreSQL16 migration005และ synthetic formulary import ผ่าน
- Frontend lint/typecheck/normal build/Vercel export ผ่าน ยังไม่ได้ตรวจ deployment Vercel จริงจากภายนอก และไม่ได้ส่ง XLS โรงพยาบาลไป hosting โดยอัตโนมัติ
- PDF เปิดอ่านข้อความหน้า53และดูรูปหน้า54โดยตรง เก็บเฉพาะ metadata/checksum และ excerpt สั้น ไม่มี approved active rules เพิ่มและไม่มี actionable alternative dosing
