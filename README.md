# Renal Smart CDSS — โรงพยาบาลมหาวิทยาลัยพะเยา

ต้นแบบวิจัย Phase 1 ใช้ **SYNTHETIC DATA เท่านั้น** ห้ามใช้กับผู้ป่วยจริง ไม่มีขนาดยาที่ได้รับการรับรอง ไม่มีการเขียนกลับ HOSxP

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

เปิด frontend port 3000 ผ่านระบบพัฒนาในเครื่อง เลือก physician และใช้รหัสผ่านที่ตั้ง ส่งข้อเสนอหรือ Override พร้อมเหตุผล จากนั้นออกจากระบบและเข้าเป็น pharmacist เพื่อตรวจ ยืนยัน ปฏิเสธ หรือขอข้อมูลเพิ่ม ตรวจ audit ด้วย pharmacist/admin และดู dashboard

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
- คำนวณ Cockcroft–Gault, แปลงหน่วย SCr, ตรวจแล็บเก่า/อนาคต ข้อมูลไม่ครบ ไตไม่คงที่/ฟอกไต และการยืนยันน้ำหนัก
- ข้อเสนอแพทย์และเภสัชกรตรวจอิสระ มี audit append-only ระดับ ORM
- Session cookie HttpOnly, role checks, expiration, input validation
- ฐานข้อมูลยา 10 รายการที่ยังไม่ยืนยัน, versioned draft rules, ปิดการอนุมัติ/เปิดใช้งานกฎ
- DailyMed adapter เก็บ raw response/provenance เป็น DRAFT; licensed providers คืน LICENSE_REQUIRED
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

Browser regression: `cd frontend && DEMO_PASSWORD=<รหัสที่ตั้งในเครื่อง> npx playwright test` ต้องมี Chromium (`CHROMIUM_PATH` default `/usr/bin/chromium`) ครอบคลุมแพทย์ส่งข้อเสนอ เภสัชกรปฏิเสธ และ audit

ตรวจสอบแล้วใน cloud instance: SQLite และ PostgreSQL migrations/seed, backend safety tests, lint/typecheck/build, synthetic OCR และ browser workflow. Docker image build มีข้อจำกัด DNS/เครือข่ายของ builder ใน cloud นี้; ไม่ใช่ผลทดสอบ Compose แบบครบระบบ

ผลการตรวจสอบและข้อจำกัดที่พบ: [verification](docs/verification.md)

## การเปิดผ่าน forwarded port / Preview

Frontend พอร์ต 3000 ใช้ `/api/*` บน origin เดียวกัน แล้วส่งต่อไป Backend ภายใน (`BACKEND_URL` default `http://127.0.0.1:8000`) Browser จึงไม่ต้องเข้าถึงพอร์ต 8000 โดยตรง และ session cookies ใช้กับ origin ของเว็บได้ Docker Compose ใช้ `BACKEND_URL=http://backend:8000`.

Cloud onboarding UI ของเซสชันนี้ไม่มี Preview/port forwarding ให้ผู้ใช้กดเว็บจากภายนอก การรันบนพอร์ต 3000 ภายใน cloud ไม่ทำให้เกิด public URL โดยอัตโนมัติ ต้องใช้ workspace ที่รองรับ Preview หรือ hosting ที่คุณกำหนดไว้ หากเปิดผ่าน HTTPS ให้ตั้ง `COOKIE_SECURE=true` ก่อนเริ่ม Backend.
