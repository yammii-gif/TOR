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
