# Renal Smart CDSS — โรงพยาบาลมหาวิทยาลัยพะเยา

เป้าหมายโครงการคือช่วยแพทย์ตัดสินใจในห้องตรวจและให้เภสัชกรเสนอทางเลือกเมื่อยาขาดคลัง รุ่นปัจจุบันยังเป็น Phase 1 ใช้ **SYNTHETIC DATA เท่านั้น** จนผ่านการตรวจรับระบบสำหรับหน้างานจริง ไม่มีขนาดยาที่ได้รับการรับรองและไม่มีการเขียนกลับ HOSxP ดู [แผนเปิดใช้หน้างาน](docs/clinical-deployment.md)

## เปิดออนไลน์

สำหรับ Vercel อ่าน [วิธี deploy เดโม full-stack บน Vercel](docs/vercel-demo.md) ใช้ root repository และตั้ง DEMO_PASSWORD/SESSION_SECRET ข้อมูลในเดโม serverless เป็นข้อมูลชั่วคราว ไม่รับประกันการแชร์ข้าม instances

หากไม่ต้องการเพิ่มบัตรใน Render ให้ใช้ [Hugging Face Spaces แบบ CPU basic ฟรี](docs/huggingface-free.md) โดยอัปโหลด Dockerfile ไฟล์เดียวจาก repository นี้ ไม่ต้องสร้างเว็บใหม่

[Deploy บน Render](https://render.com/deploy?repo=https://github.com/yammii-gif/TOR) เพื่อสร้างเว็บ HTTPS จาก repository นี้โดยไม่ต้องดาวน์โหลด ZIP ใช้บัญชี Render ของคุณ และอ่าน [ขั้นตอนเปิดเดโมออนไลน์](docs/online-demo.md) สำหรับรหัสผ่านและข้อจำกัดของข้อมูลชั่วคราว ลิงก์นี้เป็นหน้าสร้างบริการ ยังไม่ใช่ URL ของเว็บที่ deploy แล้ว

## เริ่มใช้งาน

ต้องมี Python 3.12+, Node 24 และ npm

```bash
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python -c 'from app.db import seed; seed()'
DEMO_PASSWORD='ตั้งรหัสผ่านเดโมของคุณ' ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

อีก terminal:

```bash
cd frontend
npm ci
npm run dev
```

เปิด frontend port 3000 ผ่านระบบพัฒนาในเครื่อง เลือก physician และใช้รหัสผ่านที่ตั้ง กรอกข้อเสนอยาแล้วกดยืนยันโดยแพทย์ รายการที่มีในคลังยืนยันได้ทันทีในต้นแบบ ไม่รอเภสัชกรอนุมัติซ้ำ หากยาขาดคลัง (Sitagliptin ใน seed จำลอง) ให้เข้าเป็น pharmacist เพื่อเสนอจากยาที่มีในคลัง แล้วแพทย์เลือกหรือปฏิเสธและระบุวิธีใช้ด้วยตนเอง ตรวจ audit ด้วย pharmacist/admin และดู dashboard

SQLite เก็บใน `/tmp/renal-smart.db` สำหรับเดโมชั่วคราว ใช้ PostgreSQL เมื่อทดสอบฐานข้อมูลถาวร: คัดลอก `.env.example` เป็น `.env` เปลี่ยนรหัสผ่าน แล้ว `docker compose up --build` PostgreSQL migrations/seed ตรวจสอบแล้ว; Docker image build ของแอปยังติด DNS ภายใน cloud builder

## ทดสอบ

```bash
cd backend
../.venv/bin/pytest -q
cd ../frontend
npm run typecheck
npm run lint
npm run build
```

## ทำแล้ว

- Thai UI 12 เมนู พร้อม dashboard/filter/CSV export
- FastAPI, SQLAlchemy models, Alembic initial migration, PostgreSQL config
- คำนวณ Cockcroft–Gault และ CKD-EPI 2021 eGFR จาก input จริง แยก reported eGFR จากแล็บ, แปลงหน่วย SCr, ตรวจแล็บเก่า/อนาคต ข้อมูลไม่ครบ ไตไม่คงที่/ฟอกไต และการยืนยันน้ำหนัก
- แพทย์ยืนยันข้อเสนอตนเองได้ทันที; เภสัชกรเสนอทางเลือกกรณียาขาดคลัง มี audit append-only ระดับ ORM; historical SUBMITTED ยังรองรับการคืน/ปฏิเสธ
- Session cookie HttpOnly, role checks, expiration, input validation
- ฐานข้อมูลยา 10 รายการที่ยังไม่ยืนยัน, versioned draft rules, ปิดการอนุมัติ/เปิดใช้งานกฎ
- Evidence adapters: UpToDate Public Search, NIDDK, KDIGO, NICE, DailyMed, PubMed เก็บต้นฉบับ/checksum/เวลาเป็น DRAFT เมื่อดึงสำเร็จจริง; Full Clinical Topics/Lexidrug/Micromedex แยกเป็น LICENSE_REQUIRED; บันทึก network failure และ SOURCE_CONFLICT
- Desktop communication API และ synthetic screenshot OCR script

## สิ่งที่จำลอง / ยังไม่ทำ

- ไม่มี clinical drug doses, validated alternatives หรือ approved active rules; ทุกการประเมินระบุ clinical review required
- Patient API เป็นข้อมูลจำลอง ไม่เชื่อม HOSxP/LIS จริง หน้า Auto Lab เป็น payload simulation
- `desktop/simulator.py --ocr` ใช้ Tesseract OCR ในเครื่อง (`tesseract-ocr` ต้องติดตั้ง) สร้างภาพในหน่วยความจำ ไม่จับหน้าจอจริง
- ไม่มี Windows window allowlist capture agent ที่ผ่านการทดสอบ; ต้องพัฒนาและตรวจสอบแยก
- Shared demo password และ role selection ใช้เพื่อเดโมเท่านั้น ไม่ใช่ production identity; sessions อยู่ใน memory
- Audit ป้องกันแก้ไขผ่าน ORM/API; DBA ยังแก้ฐานข้อมูลได้ ต้องใช้ DB privileges/triggers/WORM ก่อน production
- ไม่มี Excel native, before-after cohorts, satisfaction collection, measured OCR accuracy, clinical alert/error metrics; ค่าไม่มีข้อมูลเป็น null
- ไม่อ้างว่า Lexidrug/Micromedex หรือฉลากยาปัจจุบันถูกดึงแล้ว

ดู [clinical checklist](docs/clinical-validation.md) ก่อนพัฒนาการใช้งานจริง

## คำสั่งย่อและ Browser test

`scripts/install.sh` เตรียม dependencies, migrations, seed และ production build; `scripts/start-demo.sh` เริ่มทั้งสองบริการ ถ้าไม่ได้ตั้ง DEMO_PASSWORD จะสร้างรหัสสุ่มไว้ในไฟล์ local mode 600 และแสดงเฉพาะตำแหน่งไฟล์ ห้ามส่งค่ารหัสผ่านผ่านแชตหรือ logs

Browser regression: `cd frontend && DEMO_PASSWORD=<รหัสที่ตั้งในเครื่อง> npx playwright test` ต้องมี Chromium (`CHROMIUM_PATH` default `/usr/bin/chromium`) ครอบคลุมการคำนวณ แพทย์ยืนยัน ยาขาดคลัง→เภสัชกรเสนอ→แพทย์เลือก audit และสถานะสิทธิ์แหล่งข้อมูล

ตรวจสอบแล้วใน cloud instance: SQLite และ PostgreSQL migrations/seed, backend safety tests, lint/typecheck/build, synthetic OCR และ browser workflow. Docker image build มีข้อจำกัด DNS/เครือข่ายของ builder ใน cloud นี้; ไม่ใช่ผลทดสอบ Compose แบบครบระบบ

ผลการตรวจสอบและข้อจำกัดที่พบ: [verification](docs/verification.md)

## การเปิดผ่าน forwarded port / Preview

Frontend พอร์ต 3000 ใช้ `/api/*` บน origin เดียวกัน แล้วส่งต่อไป Backend ภายใน (`BACKEND_URL` default `http://127.0.0.1:8000`) Browser จึงไม่ต้องเข้าถึงพอร์ต 8000 โดยตรง และ session cookies ใช้กับ origin ของเว็บได้ Docker Compose ใช้ `BACKEND_URL=http://backend:8000`.

Cloud onboarding UI ของเซสชันนี้ไม่มี Preview/port forwarding ให้ผู้ใช้กดเว็บจากภายนอก การรันบนพอร์ต 3000 ภายใน cloud ไม่ทำให้เกิด public URL โดยอัตโนมัติ ต้องใช้ workspace ที่รองรับ Preview หรือ hosting ที่คุณกำหนดไว้ หากเปิดผ่าน HTTPS ให้ตั้ง `COOKIE_SECURE=true` ก่อนเริ่ม Backend.

สูตร ขอบเขต และกรณีทดสอบการคำนวณ: [renal calculations](docs/renal-calculations.md)

อ่านแถบแล็บในเครื่อง: `python desktop/lab_region.py` ดู [Desktop Agent](docs/desktop-agent.md) ไม่อัปโหลดภาพ ไม่จับหน้าต่างอัตโนมัติ และไม่ยืนยันตัวผู้ป่วยจากแถบแล็บเพียงอย่างเดียว

นโยบายแหล่งอ้างอิงและโครงสร้างกฎปรับยา: [renal reference policy](docs/renal-reference-policy.md)

## ประเมินอัตโนมัติและบัญชียาโรงพยาบาล

หน้าแพทย์/ยาทางเลือกประเมินซ้ำอัตโนมัติเมื่อเปลี่ยนยา ข้อบ่งใช้ หรือข้อมูลไต ซ่อนผลเก่า แยกข้อค้นพบ Metformin จาก PDF ที่ผู้ใช้แนบ (หน้าเอกสาร37–38) ออกจากคำตัดสินที่ยังรอรับรอง ไม่มีการเปิดกฎจากเอกสารอัตโนมัติ ดู [automatic assessment](docs/automatic-medication-assessment.md)

เพิ่มนำเข้า XLS และค้นบัญชียาแยกผลิตภัณฑ์โดย pharmacist/admin ที่ฐานความรู้ยา ไฟล์โรงพยาบาลตรวจพบ827รายการและนำเข้า local แล้ว แต่ช่องสถานะคลังว่าง จึงเป็น UNKNOWN ไม่ถือว่ามีของ/ใช้แทนได้ ไม่ commit ข้อมูลบัญชียาจริงหรือราคาเข้า source ดู [hospital formulary](docs/hospital-formulary.md) ก่อนนำเข้าบน hosting
