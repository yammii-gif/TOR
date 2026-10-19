# เปิดเว็บออนไลน์ด้วย Render

ใช้ source เดิม ไม่ต้องดาวน์โหลด ZIP และไม่ต้องเปิดคอมพิวเตอร์ส่วนตัวค้างไว้

1. เปิด https://render.com/deploy?repo=https://github.com/yammii-gif/TOR แล้วเข้าสู่ระบบ Render
2. เชื่อม GitHub และอนุญาตให้ Render อ่าน repository `yammii-gif/TOR`
3. ตรวจ Blueprint ที่อ่านจาก `render.yaml` และเลือกสร้างบริการตามหน้าจอ Render
4. เมื่อ build/deploy เสร็จ เปิด URL HTTPS ที่ Render แสดงในหน้า service (ใช้ URL จริงจาก Render ไม่คาดเดาชื่อ URL)
5. ไปหน้า Environment ของ service เพื่อดู/กำหนด `DEMO_PASSWORD` แล้วใช้รหัสนั้นเข้าสู่เว็บ เลือก physician หรือ pharmacist ห้ามส่งรหัสผ่านผ่านแชต

Blueprint ใช้แผน free ตามที่ Render รองรับ ต้องตรวจเงื่อนไขและข้อจำกัดปัจจุบันของบัญชีก่อนสร้าง service ไม่ได้สร้างบริการหรือยอมรับค่าใช้จ่ายให้ผู้ใช้โดยอัตโนมัติ

## สิ่งที่รัน

- Web service เดียว: Next.js เปิดพอร์ต `$PORT` ของโฮสต์; `/api/*` ส่งไป FastAPI ภายในที่ loopback port 8000
- FastAPI ไม่เปิดพอร์ตสู่ภายนอกโดยตรง, session cookie ตั้ง Secure สำหรับ HTTPS
- Alembic migrations และ seed ข้อมูล SYNTHETIC DATA เริ่มอัตโนมัติ
- SQLite อยู่ใน `/tmp`: ใช้ทดลองชั่วคราว ข้อมูลที่กรอกและ sessions อาจหายเมื่อบริการ restart/redeploy ไม่ใช้จัดเก็บข้อมูลวิจัยจริง
- Free service อาจ sleep เมื่อไม่มีการใช้งานและเปิดครั้งแรกช้า
- ไม่มี integration กับ HOSxP หรือกฎขนาดยาที่ได้รับการรับรอง

## ตรวจสอบหลัง deploy

เปิด `/api/health` บนโดเมนของ service ต้องได้ `status: ok` และ `mode: SYNTHETIC DATA` จากนั้นเข้าสู่บทบาท physician, คำนวณ CrCl ของกรณี SYN-001, ส่งข้อเสนอ และเข้าสู่ pharmacist เพื่อปฏิเสธ/ขอข้อมูลเพิ่มเติม ตรวจ Audit และ Dashboard

ไฟล์ deploy และ startup script สามารถทดสอบใน cloud workspace ได้ แต่การ deploy จริงและ URL จะเกิดหลังผู้ใช้เชื่อมบัญชี Render และสร้าง service สำเร็จเท่านั้น
