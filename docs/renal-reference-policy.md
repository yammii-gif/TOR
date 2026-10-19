# ลำดับอ้างอิง Renal Dose Adjustment

1. UpToDate Lexidrug (เดิม Lexicomp) / Micromedex: ขนาดยา ข้อห้าม คำแนะนำทางคลินิก เมื่อหน่วยงานมีสิทธิ์และวิธีเชื่อมต่อที่อนุญาต ไม่ scrape เนื้อหาปิด
2. FDA Prescribing Information / DailyMed: ตรวจเกณฑ์ปรับยาตามฉลากที่ตรง formulation, indication, population และฉบับ วันที่ระบุจริง ผล search/listing ไม่ใช่ฉลากยาเต็ม
3. KDIGO / NKF: สนับสนุนเกณฑ์ประเมินการทำงานของไตและคำแนะนำเฉพาะโรค ไม่ใช้แทน renal dosing monograph โดยอัตโนมัติ

ลำดับนี้เป็นนโยบายเลือกแหล่งอ้างอิง ไม่ใช่หลักฐานว่าข้อมูลใดถูกต้องหรือเหนือกว่าเมื่อข้อแนะนำขัดกัน ต้องติดธง SOURCE_CONFLICT แล้วให้เภสัชกรตรวจ ไม่เฉลี่ยหรือเลือกขนาดยาเอง

`Rule.specification` เป็น versioned JSON มี template ใน `backend/app/rule_specification.py`: generic/brand, indications, formulation, usual dose, renal measure/unit, thresholds, adjusted dose/route/interval/duration, applicable conditions/exclusions, contraindications/precautions/interactions, administration/adverse effects/monitoring, alternatives/rationale, sources, checked_at/reviewer, evidence_level/grading_system และ institutional_approval

แต่ละ `sources` entry เมื่อกรอกจริงต้องมี source_name, URL, document_version/revision, accessed_at, exact_excerpt และตำแหน่ง section/page; เชื่อม `evidence_record_id` และ SHA-256 ของต้นฉบับเมื่อ import ได้ ระบุขอบเขต threshold รวม/ไม่รวม และหน่วยอย่างชัดเจน ห้ามแปลง CrCl เป็น eGFR เพียงเพราะเป็นตัวเลขใกล้กัน

ยังไม่มีค่าขนาดยาใน template ทุกช่องว่างหมายถึงยังไม่ยืนยัน ไม่ใช่ไม่มีข้อห้าม ระดับหลักฐานต้องระบุ grading system และผู้ทบทวน ห้ามเดาจากชื่อ source ขั้น APPROVED/ACTIVE ยังถูกปิดไว้จนมี clinical governance ที่ตรวจรับแล้ว

เภสัชกรทบทวนความรู้ของกฎก่อนเปิดใช้ แยกจาก workflow ใบสั่งยา: แพทย์ไม่ต้องรอเภสัชกรอนุมัติทุกครั้ง เภสัชกรเสนอทางเลือกเฉพาะกรณียาขาดคลังตามที่ผู้ใช้กำหนด
