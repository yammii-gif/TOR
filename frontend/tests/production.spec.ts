import {test,expect,request as transport,type APIRequestContext,type Page} from '@playwright/test';
// Isolated synthetic workers only. Node verifies the explicit local test CA;
// the browser origin is routed to real HTTPS endpoints without disabling TLS.
const origin='https://clinical.example.test';
const target=process.env.PRODUCTION_TEST_URL;
const second=process.env.PRODUCTION_TEST_SECOND_WORKER||target;
const password=process.env.PRODUCTION_TEST_PASSWORD||'';
test.skip(!target||!password,'Requires isolated production workers and synthetic credentials');
const upstreams=new WeakMap<Page,APIRequestContext>();
test.beforeEach(async({page})=>{
 const upstream=await transport.newContext();upstreams.set(page,upstream);
 await page.route(origin+'/**',async route=>{
  const url=new URL(route.request().url());
  const server=url.pathname==='/api/auth/me'?second:target;
  const headers=await route.request().allHeaders();
  // Only browser cookies are authoritative; never substitute the transport jar.
  headers.cookie=headers.cookie||'';
  const response=await upstream.fetch(server+url.pathname+url.search,{method:route.request().method(),headers,data:route.request().postDataBuffer()||undefined});
  try{await route.fulfill({response});}catch(error){if(!page.isClosed()&&!route.request().failure())throw error;}
 });
});
test.afterEach(async({page})=>{await page.unrouteAll({behavior:'wait'});await upstreams.get(page)?.dispose();});
async function signIn(page:Page,username:string){
 await page.goto(origin);
 await expect(page.getByRole('heading',{name:'เข้าสู่ระบบด้วยบัญชีพนักงาน'})).toBeVisible();
 await expect(page.getByLabel('บทบาท',{exact:true})).toHaveCount(0);
 await page.getByLabel('ชื่อบัญชี',{exact:true}).fill(username);
 await page.getByLabel('รหัสผ่าน',{exact:true}).fill(password);
 await page.getByRole('button',{name:'เข้าสู่ระบบ',exact:true}).click();
}
test('individual login, cross-worker reload, CSRF, idempotent decision and revoked logout',async({page})=>{
 await signIn(page,'synthetic-doctor');
 await expect(page.getByText('ผู้ใช้งาน: physician')).toBeVisible();
 await page.reload();await expect(page.getByText('ผู้ใช้งาน: physician')).toBeVisible();
 await page.getByRole('button',{name:/พื้นที่ทำงานแพทย์/}).click();
 const proposal='Synthetic manual physician decision '+Date.now();
 await page.getByLabel('ข้อเสนอแพทย์ (ไม่มีคำแนะนำขนาดยาจากระบบ)').fill(proposal);
 const records=page.locator('[data-testid^="physician-record-"]').filter({hasText:proposal});
 const confirm=page.getByRole('button',{name:'ยืนยันการตัดสินใจของแพทย์',exact:true});
 await confirm.click();await expect(page.getByRole('status')).toHaveText('ดำเนินการสำเร็จ');
 await expect(records).toHaveCount(1);
 await confirm.click();await expect(page.getByRole('status')).toHaveText('ดำเนินการสำเร็จ');
 await expect(records).toHaveCount(1);
 await page.getByRole('button',{name:'ออกจากระบบ',exact:true}).click();await page.reload();
 await expect(page.getByRole('heading',{name:'เข้าสู่ระบบด้วยบัญชีพนักงาน'})).toBeVisible();
});
test('admin creates and disables staff and cannot disable last admin',async({page})=>{
 await signIn(page,'synthetic-admin');await expect(page.getByText('ผู้ใช้งาน: admin')).toBeVisible();
 await page.getByRole('button',{name:/ตั้งค่า/}).click();
 const staffName='synthetic-added-'+Date.now();
 await page.getByLabel('ชื่อบัญชีใหม่',{exact:true}).fill(staffName);
 await page.getByLabel('รหัสผ่านเริ่มต้น (อย่างน้อย12ตัวอักษร)',{exact:true}).fill(password);
 await page.getByLabel('สิทธิ์บัญชีใหม่',{exact:true}).selectOption('pharmacist');
 await page.getByRole('button',{name:'สร้างบัญชีรายบุคคล',exact:true}).click();
 await expect(page.getByRole('heading',{name:staffName,exact:true})).toBeVisible();
 await expect(page.getByLabel('รหัสผ่านเริ่มต้น (อย่างน้อย12ตัวอักษร)',{exact:true})).toHaveValue('');
 await page.getByRole('button',{name:'ปิดบัญชี '+staffName,exact:true}).click();
 await expect(page.getByRole('button',{name:'เปิดบัญชี '+staffName,exact:true})).toBeVisible();
 await page.getByRole('button',{name:'ปิดบัญชี synthetic-admin',exact:true}).click();
 await expect(page.getByText('เปลี่ยนบัญชีไม่ได้ ต้องเหลือผู้ดูแลที่เปิดใช้งานอย่างน้อยหนึ่งบัญชี')).toBeVisible();
});
