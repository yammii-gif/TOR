# รายการตรวจสอบก่อนใช้งานคลินิก

- [ ] การอนุมัติใช้งานโดยสถาบัน PDPA และ data governance; จริยธรรมวิจัยเฉพาะกรณีทำวิจัย
- [ ] ผู้เชี่ยวชาญตรวจสูตร Cockcroft–Gault และ weight policy ในแต่ละกลุ่ม (ต้นแบบรับ actual weight เฉพาะเมื่อยืนยันว่าเหมาะสม ไม่รองรับเด็ก/อ้วน/บวมน้ำโดยอัตโนมัติ)
- [ ] ตรวจนโยบาย lab recency: 48 ชั่วโมงเป็นค่าตัวอย่าง ไม่ใช่มาตรฐานทั่วไป
- [ ] ข้อมูลยาทุกรายการต้องมี generic/brand, indication, form/strength, usual dose, renal measure/threshold, adjusted dose/interval, contraindications/precautions, administration, adverse effects, monitoring, alternatives/rationale
- [ ] Evidence JSON/specification ต้องมี exact source quote, source URL/version/access date/reviewer และตรวจ SOURCE_CONFLICT; schema metadata แบบ JSON ใน Phase 1 ยังต้องเพิ่ม typed validation ก่อนอนุมัติ
- [ ] Review workflow DRAFT → PENDING_REVIEW → APPROVED → ACTIVE → RETIRED ต้องแยกผู้จัดทำ/ผู้อนุมัติ มีลายเซ็นและการทดสอบ boundary ทุกกฎ ก่อนปลด activation block
- [ ] ทดสอบ therapeutic alternatives แยกตาม indication/allergy/interactions/comorbidities/formulary
- [ ] ตรวจรับบัญชีรายบุคคล/session revocation/CSRF/rate limitsที่เพิ่มในรุ่น2.3; กำหนดMFA/access reviewและSSOภายหลังหากมี พร้อมHTTPS/TLS, secure cookies และsecrets management
- [ ] DB least privilege, encrypted backups, immutable external audit และ retention policy
- [ ] Structured read-only HOSxP/LIS integration ก่อนพิจารณา OCR
- [ ] Windows agent: explicit consent, approved window/region only, pause/stop, 2–3s polling, identity switch quarantine, timestamp/unit checks, no screenshot retention
- [ ] Software verification, clinical validationในขั้นตอนที่หน่วยงานอนุมัติ, การรับรองกฎยาร่วมแพทย์/เภสัชกร และincident response (ไม่ใช่บังคับเภสัชกรยืนยันใบสั่งทุกราย)
