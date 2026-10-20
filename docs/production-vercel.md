# ตั้งค่า Vercel + PostgreSQL ถาวร + บัญชีรายบุคคล (รุ่น2.3)

เป้าหมายผู้ใช้: ใช้ Vercel เดิม ฐานข้อมูลภายนอกแบบฟรี ไม่ผูกบัตร และยังไม่มี SSO รุ่นนี้เตรียมโครงสร้าง production hosting แล้ว แต่ **ยังไม่ใช่การอนุมัติให้ใช้กับผู้ป่วยจริง**: patient data ยังคง SYNTHETIC และไม่มีกฎยา approved ACTIVE

## สิ่งที่เปลี่ยน

- `APP_ENV=production` ต้องมี PostgreSQL ที่เข้ารหัสและตรวจ certificate (`sslmode=verify-full`) ไม่ fallback ไป SQLite และไม่ยอมใช้ DEMO_PASSWORD/role selector
- บัญชีรายบุคคลใช้ salted scrypt; ผู้ดูแลกำหนด role การล็อกอินไม่เชื่อ role จาก browser
- session เก็บเป็น hash ในฐานข้อมูล อายุ4ชั่วโมง ใช้ร่วมกันข้ามinstancesได้ ออกจากระบบ/ปิดบัญชี/เปลี่ยนสิทธิ์/ตั้งรหัสผ่านใหม่จะเพิกถอนsession
- SameSiteStrict + Secure + HttpOnly session cookie; CSRF tokenและOrigin validationสำหรับคำขอเปลี่ยนข้อมูล; จำกัดล็อกอิน5ครั้งต่อ15นาทีต่อบัญชีในฐานข้อมูล
- ผู้ดูแลสร้าง/ปิด/เปลี่ยนสิทธิ์บัญชีได้ที่ตั้งค่า ไม่ให้ปิดผู้ดูแลคนสุดท้าย ไม่มี public signup
- PostgreSQLมีaudit triggersป้องกันUPDATE/DELETE/TRUNCATE พร้อมแยกruntime roleจากmigration owner ข้อมูลเดิมยังต้องมีbackupและการกำกับสิทธิ์DBA
- การส่งข้อเสนอแพทย์มีIdempotency-Keyและตรวจpayload ป้องกันบันทึกซ้ำจากคำขอเดิม
- `/api/health/live` ตรวจprocess; `/api/health/ready` ตรวจDB/schema/admin/runtime privileges แยกจาก `clinical_ready:false`

## 1. สร้างฐานข้อมูลภายนอก

ตัวเลือกเริ่มต้นคือ Neon Free: เปิด `https://neon.tech/` สมัครบัญชีและเลือกFree ไม่เปิดpaid planหรือเพิ่มบัตร หากขั้นตอนสมัครของคุณบังคับบัตร ให้หยุดแล้วเลือกผู้ให้บริการ/บัญชีที่รองรับเงื่อนไขนี้ ไม่ถือว่ามีการอนุมัติค่าใช้จ่าย

เลือกregionที่หน่วยงานอนุมัติ สร้างproject/databaseเฉพาะแอปนี้ คัดลอกconnection stringไปเก็บผ่านช่องทางsecure ห้ามส่งในแชตหรือcommit แผนฟรี/โควตา/ระยะพักบริการต้องตรวจจากผู้ให้บริการปัจจุบัน ที่นี่ไม่ได้สร้างบัญชีNeonหรือเชื่อมฐานข้อมูลจริงให้แล้ว

ผู้ดูแลใช้ **direct owner URL** สำหรับmigrations/provision/restore ส่วนVercelใช้ **pooled endpointและruntime role** ปกติhostมี `-pooler` เพื่อรองรับหลายinstancesอย่างประหยัดconnection ตรวจURLที่ผู้ให้บริการออกให้ ไม่เดาชื่อhost

แผนฟรีไม่รับประกันavailabilityตลอดเวลา อาจcold start/suspend/ชนquota จึงต้องกำหนดแผนสำรองสำหรับหน้างานและประเมินSLAก่อนใช้จริง ห้ามใช้โครงการfreeที่ยังไม่ผ่านreviewเก็บข้อมูลผู้ป่วยจริง

## 2. เตรียมเครื่องผู้ดูแล

ใช้เครื่องที่ไว้ใจได้ ติดตั้งPython3.12+ และbackend dependencies เก็บconfigนอกrepositoryด้วยสิทธิ์600 (Windowsใช้ACLส่วนบุคคล):

```bash
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cp .env.production.example /secure/renal-owner.env
chmod 600 /secure/renal-owner.env
```

แก้ไฟล์ด้วยeditorที่ปลอดภัย: APP_ENV=production, CLINICAL_DATA_MODE=synthetic, COOKIE_SECURE=true, FRONTEND_ORIGIN=URLเว็บHTTPSจริงแบบไม่มีpath, SESSION_SECRETสุ่มอย่างน้อย32ตัว และDATABASE_URLของowner

ใช้ `sslmode=verify-full` แทน `sslmode=require` ในURL เครื่องใช้systemCAหากไม่ได้ระบุsslrootcert ไม่ปิดTLSเพื่อแก้การเชื่อมต่อ รหัสผ่านในURLต้องpercent-encodeตามมาตรฐาน; provider URLที่คัดลอกมามักencodeแล้ว

## 3. Migrate และสร้างผู้ดูแลคนแรก

```bash
.venv/bin/python scripts/prepare-production.py --env-file /secure/renal-owner.env
.venv/bin/python scripts/manage-staff.py --env-file /secure/renal-owner.env create --username hospital-admin --role admin
```

รหัสผ่านอ่านผ่านhidden promptสองครั้ง ไม่ส่งเป็นargument/log ขั้นตอนprepareรันAlembicแบบtransactionพร้อมadvisory lockและseedบัญชียา827รายการ/ผู้ป่วยสังเคราะห์ ไม่รันmigrationsในทุกVercelrequest ไม่รันบนฐานข้อมูลที่หน่วยงานใช้ร่วมกับโปรแกรมอื่นโดยไม่ตรวจทาน

## 4. แยก runtime role

```bash
.venv/bin/python scripts/provision-runtime-role.py --env-file /secure/renal-owner.env --role renal_runtime --runtime-host HOST_POOLER_ที่ผู้ให้บริการระบุ --output /secure/renal-runtime-url.env
```

คำสั่งถามรหัสผ่านDBของruntimeแบบซ่อนอย่างน้อย24ตัว สร้างroleที่ไม่เป็นsuperuser/ไม่สร้างDBหรือrole ไม่ให้CREATEในpublic ไม่มีสิทธิ์แก้auditหรือalembic_version เขียนURLเฉพาะไฟล์600 ไม่แสดงcredentialในterminal หากproviderไม่อนุญาตCREATE ROLEผ่านSQL ให้ฝ่ายITสร้างroleสิทธิ์เทียบเท่าและตรวจreadiness ไม่ใส่owner URLให้Vercel

หลังmigrationใหม่ที่เพิ่มตาราง ให้ทบทวน/เพิ่มgrantsเฉพาะruntime roleตามที่จำเป็น ไม่ยกให้เป็นownerเพื่อแก้permission error

## 5. ตั้งค่า Vercel Production เท่านั้น

ที่โปรเจกต์เดิม → Settings → Environment Variables:

| ตัวแปร | ค่าที่ต้องใช้ |
| --- | --- |
| APP_ENV | production |
| CLINICAL_DATA_MODE | synthetic |
| DATABASE_URL | pooled URLของruntimeจากไฟล์private, sslmode=verify-full |
| FRONTEND_ORIGIN | originHTTPSที่ใช้กดVisitของProductionจริง เช่น https://ชื่อเว็บ.vercel.app ไม่มีpath |
| COOKIE_SECURE | true |
| SESSION_SECRET | ค่าสุ่มของproductionอย่างน้อย32ตัว ใส่ในsecure field |

ไม่ตั้งDEMO_PASSWORDให้production ไม่แชร์DB/credentialsproductionไปPreviewหรือbranchที่ยังไม่ตรวจทาน Previewอาจคงdemoแยกข้อมูลไว้ การเลือกScopeผิดอาจทำให้Previewlogin403หรือเผลอใช้ฐานข้อมูลร่วมกัน

Deployรุ่น2.3แล้วเปิดVisit ต้องเห็น **เข้าสู่ระบบด้วยบัญชีพนักงาน** และไม่มีช่องเลือกบทบาท ล็อกอินด้วยผู้ดูแลที่สร้างแล้ว → ตั้งค่า → สร้างบัญชีแพทย์/เภสัชกรเป็นรายบุคคล ส่งรหัสผ่านผ่านช่องทางsecureของหน่วยงาน ห้ามใช้บัญชีร่วม

## 6. ตรวจรับระบบที่deployจริง

ตรวจแบบread-onlyจากเครื่องที่เข้าถึงเว็บไซต์ได้: `python scripts/check-production.py https://URLเว็บจริง` คำสั่งตรวจTLSตามปกติ ไม่ส่งcredentialsและไม่แก้ข้อมูล หากล้มเหลวจะexit2 ไม่อ้างว่าdeploymentพร้อม


- `/api/health/live` ตอบalive และ `/api/health/ready` ตอบ200พร้อมchecksเป็นtrue; ถ้า503ตรวจschema/admin/สิทธิ์DB ไม่แก้โดยเปิดSQLiteหรือใช้owner URL
- ล็อกอินแพทย์ คำนวณจากข้อมูลสังเคราะห์ ยืนยันข้อเสนอ กดส่งเดิมซ้ำแล้วต้องไม่เพิ่มรายการซ้ำ
- reload/เปิดsessionข้ามinstance ข้อมูล/บัญชีต้องคงอยู่; logoutแล้วsessionเดิมต้องใช้ไม่ได้
- ทดสอบเภสัชกรเสนอเฉพาะยาหมดจากผลิตภัณฑ์ที่ตรวจแล้วมีในคลัง ตรวจrole/audit
- นำเข้าPDFไกด์ไลน์และบัญชียา ค้นได้หลังcold start ฐานข้อมูลถาวรต้องเก็บไฟล์เหล่านี้อยู่
- ตรวจbackup/restoreด้านล่าง รวมการกู้ข้อมูลในฐานข้อมูลแยก และทบทวนแผนfallbackเมื่อบริการฟรีไม่พร้อม

ยังไม่ได้ตรวจpublicVerceldeploymentจากเซสชันนี้ เนื่องจากไม่มีสิทธิ์เข้าบัญชีVercel/Neonที่ใช้งานจริงและยังไม่มีDATABASE_URLของผู้ใช้

## Backupที่เข้ารหัสและการกู้คืน

ติดตั้งPostgreSQL clientที่majorversionตรงกับserver และoperator dependenciesบนเครื่องปลอดภัย ไม่รันbackupในVercelfunction:

```bash
.venv/bin/pip install -r backend/requirements-ops.txt
.venv/bin/python scripts/database-backup.py keygen --file /secure/renal-backup.agekey
.venv/bin/python scripts/database-backup.py --env-file /secure/renal-owner.env backup --file /secure/backups/renal-backup.age --recipient PUBLIC_AGE_RECIPIENT_จากkeygen
```

privateidentityอยู่offlineคนละที่กับbackup ห้ามcommit/.แชร์ คำสั่งkeygenแสดงเฉพาะpublicrecipient ใช้ageผ่านpyrageสำหรับauthenticated encryption เก็บplaintextpg_dumpเฉพาะmemoryของเครื่องผู้ดูแลและเขียนbackup/manifestแบบ600 ควรมีRAMพอสำหรับdumpที่บีบอัดและencryptedcopy เช่นเครื่องผู้ดูแลอย่างน้อย4GBสำหรับโควตาDBเล็ก ไม่ใช้serverlessเพื่อทำbackup

ตั้งscheduleบนเครื่องที่หน่วยงานดูแล (เช่นรายวันตามRPOที่อนุมัติ) พร้อมmonitorผลสำเร็จและเก็บสำเนาเข้ารหัสนอกprovider เก็บกุญแจแยกและทดสอบกู้คืนสม่ำเสมอ แผนนี้ยังไม่ได้ตั้งschedulerจริงให้โรงพยาบาล

กู้คืนไปยัง **ฐานข้อมูลแยกที่ว่าง** ซึ่งมีowner configของตัวเอง:

```bash
.venv/bin/python scripts/database-backup.py --env-file /secure/renal-restore-target.env restore --file /secure/backups/renal-backup.age --identity /secure/renal-backup.agekey --confirm-database ชื่อฐานข้อมูลกู้คืน
```

ตรวจchecksumและถอดรหัสให้สำเร็จก่อนส่งplaintextเข้าpg_restoreแบบsingletransaction ปฏิเสธtargetที่มีตารางอยู่ ไม่ลบฐานข้อมูลใช้งาน หลังrestoreให้ตรวจschema/catalog/accounts/audit สร้างruntime role/grantsให้ตรงtarget ทดสอบก่อนเปลี่ยนURLจริง การcutoverจริงต้องเป็นขั้นตอนที่หน่วยงานอนุมัติ

## ขอบเขตความพร้อมที่ยังต้องทำ

ระบบนี้ยังไม่รับข้อมูลผู้ป่วยจริง/ไม่มีHOSxPread-onlyintegrationที่ตรวจรับ/ไม่มีกฎขนาดยาที่approvedACTIVE ต้องผ่านclinical validation, PDPA/data residency, security review/penetration test, account lifecycle/MFA policy และincident responseก่อนเปิดหน้างาน ผู้มีสิทธิ์DBAยังเปลี่ยนschemaได้ จึงต้องมีการกำกับและauditภายนอกเพิ่มเติม ไม่ถือว่าtriggersทดแทนWORMหรือgovernance
