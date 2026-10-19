# Vercel: full-stack synthetic demo

ใช้ repository เดิม โดย Vercel serve static export ของหน้า Next.js และ Python Function ที่ใช้ FastAPI/SQLAlchemy เดิม ไม่ต้องมี Render หรือ Hugging Face backend

## ตั้งค่าผ่านบัญชี Vercel

1. เปิด https://vercel.com/new เลือก Import repository `yammii-gif/TOR`, branch main
2. Root Directory ต้องเป็น root ของ repository (`.`) ไม่เลือก `frontend` เพราะต้องรวม Python function ด้วย ใช้ framework preset Other หากระบบถาม และใช้ `vercel.json` ที่เตรียมไว้
3. เพิ่ม Environment Variables ก่อน deploy:
   - `DEMO_PASSWORD`: รหัสเข้าสู่เดโมที่คุณตั้งเอง
   - `SESSION_SECRET`: ค่าสุ่มอย่างน้อย 32 ตัวอักษรสำหรับลงลายเซ็น session เก็บเป็น sensitive variable
4. ใช้บัญชี/แผน Hobby ที่มีสิทธิ์ใช้งานโดยไม่มีค่าใช้จ่ายตามเงื่อนไขปัจจุบัน หากหน้าจอขอบัตรหรือเสนอค่าใช้จ่าย ให้หยุด ไม่เพิ่มบริการฐานข้อมูลหรือแพ็กเกจที่เสียเงิน
5. Deploy แล้วใช้ URL จริงจากหน้า Vercel ไม่เดาชื่อโดเมน เมื่อพร้อม เปิด `/api/health` ต้องได้ `status: ok` และ `mode: SYNTHETIC DATA`
6. เข้าสู่เว็บด้วยรหัสที่ตั้งและเลือก physician/pharmacist ห้ามส่งรหัสหรือ SESSION_SECRET ผ่านแชต

## ข้อจำกัดที่ต้องเห็นก่อนทดลอง

- นี่คือ serverless simulation เท่านั้น SQLite ใน `/tmp` ไม่รับประกัน persistence หรือการแชร์ข้อมูลระหว่าง function instances รายการที่แพทย์สร้างอาจไม่ปรากฏใน instance ของเภสัชกร หากระบบกระจาย requests ห้ามใช้เก็บข้อมูลวิจัยจริง
- UI แสดงคำเตือน SERVERLESS DEMO โดยตรง การทดสอบ workflow ในเครื่องพิสูจน์ instance เดียว ไม่ใช่ multi-instance consistency
- session แบบ HMAC มีอายุ 4 ชั่วโมงและตรวจลายเซ็นได้ข้าม process โดยไม่ใช้ memory store การ logout ลบ cookie ใน browser; token ที่ถูกคัดลอกไว้ยังใช้ได้ถึงหมดอายุ การเปลี่ยน SESSION_SECRET ยกเลิก token ทั้งหมด
- หากต้องการทดลองหลายผู้ใช้โดยเก็บผลต่อเนื่อง ต้องตั้ง shared PostgreSQL ที่ได้รับอนุญาตและรัน Alembic migrations ก่อนใช้งาน ไม่เพิ่มบริการฐานข้อมูลที่คิดเงินให้อัตโนมัติ
- ไม่มี real HOSxP หรือ active clinical dose rules ใช้เฉพาะ synthetic patients

## Implementation และตรวจสอบในเครื่อง

`vercel.json` กำหนด static builder และ Python builder; `api/index.py` mount API เดิมที่ `/api`. `npm --prefix frontend run vercel-build` build จาก temporary copy เพื่อเอา Next proxy ออกเฉพาะ static export โดยไม่แก้ build ปกติ Export อยู่ใน `frontend/out` และไม่ commit generated outputs.

ตรวจ backend ด้วย `.venv/bin/python -m pytest -q`; export ผ่าน และ browser tests ผ่านเมื่อ serve exported frontend กับ Python adapter ใน process เดียวกัน Vercel routing/build/runtime จริงยังต้องตรวจหลัง deploy ในบัญชีผู้ใช้ ไม่อ้างว่าได้ deploy แล้วเพียงเพราะ local checks ผ่าน
