# เดโมฟรีบน Hugging Face Spaces

ใช้ **Docker → Blank → CPU basic (Free)** ซึ่งโดยทั่วไปไม่ต้องเพิ่มบัตร หากบัญชีหรือหน้าจอของผู้ให้บริการขอบัตรหรือแสดงราคา ให้หยุดและตรวจเงื่อนไขก่อน ไม่เลือก GPU, paid CPU หรือ persistent storage

1. สมัคร/เข้าสู่ระบบ https://huggingface.co แล้วกด https://huggingface.co/new-space
2. ตั้งชื่อ `renal-smart-cdss` เลือก SDK **Docker**, template **Blank**, hardware **CPU basic (Free)** และ visibility **Public** แล้ว Create Space
3. ไป **Settings → Variables and secrets** เพิ่ม **Secret** ชื่อ `DEMO_PASSWORD` กำหนดรหัสผ่านเดโมของคุณเอง ห้ามส่งรหัสผ่านผ่านแชต
4. ใน Space ไป **Files → Add file → Create a new file** ตั้งชื่อ `Dockerfile` แล้วคัดลอกเนื้อหาจาก https://github.com/yammii-gif/TOR/blob/main/Dockerfile มาวางและ commit หากมีไฟล์ชื่อเดิม ให้แก้ไขไฟล์นั้นแทน
5. รอ build เสร็จและขึ้น Running แล้วกดเปิดแอปในแท็บใหม่จากหน้า App ใช้ URL `.hf.space` ที่ระบบแสดงจริง เพราะ login cookie แบบ Strict อาจไม่ทำงานใน iframe
6. ใช้รหัสที่ตั้งในข้อ 3 แล้วเลือก physician หรือ pharmacist

ไม่ต้องอัปโหลด source อีก 38 ไฟล์: Dockerfile ดึง snapshot โค้ดเดิมจาก GitHub commit `140ab3477b369c7e04603276635799b6e23638da` และตรวจ SHA-256 ก่อน build ต้องให้ snapshot นั้นอ่านได้จากสาธารณะ ไม่ใส่ GitHub token ใน Dockerfile และไม่เปลี่ยน repository เป็น public โดยอัตโนมัติ ถ้า repository ไม่เป็น public ให้ใช้การอัปโหลด source ที่ได้รับอนุญาตแยกต่างหาก

ข้อมูลเป็น SYNTHETIC DATA เท่านั้น SQLite อยู่ในพื้นที่ชั่วคราวและอาจหายเมื่อ Space restart/sleep/rebuild ไม่เชื่อม HOSxP และยังไม่มี clinical dose rules ที่ได้รับการรับรอง

ใน cloud นี้ตรวจดาวน์โหลด archive/checksum และเทียบ source กับ Git commit ได้แล้ว รวมถึง build/start scripts และ workflow ของ snapshot ที่ผ่านการทดสอบก่อนหน้า ยังไม่อ้างว่าได้สร้าง Space หรือ Docker image บน Hugging Face สำเร็จจนกว่าจะเห็นผล build จริงในบัญชีผู้ใช้
