'use client';
import {useEffect,useState} from 'react';
type Item={code:string;display_name:string;generic_name:string;strength:string;dosage_form:string;stock_status:string;stock_checked_at:string|null;source_stock_flag:string;source_account_flag:string};
type Result={total:number;matched:number;items:Item[]};
const stockLabel:Record<string,string>={UNKNOWN:'ยังไม่ทราบ',IN_STOCK:'ผู้ตรวจระบุมีในคลัง',OUT_OF_STOCK:'ผู้ตรวจระบุยาหมด'};
export default function FormularyBrowser({canManage=false}:{canManage?:boolean}){
  const [q,setQ]=useState(''),[offset,setOffset]=useState(0),[revision,setRevision]=useState(0),[data,setData]=useState<Result|null>(null),[message,setMessage]=useState(''),[loading,setLoading]=useState(false),[busy,setBusy]=useState(false);
  useEffect(()=>{
    const controller=new AbortController();setLoading(true);
    const timer=setTimeout(async()=>{try{
      const response=await fetch('/api/formulary?'+new URLSearchParams({q,offset:String(offset),limit:'20'}),{credentials:'include',signal:controller.signal});
      if(!response.ok)throw Error('ไม่สามารถโหลดบัญชียาได้');
      const result=await response.json();if(!controller.signal.aborted){setData(result);setLoading(false);}
    }catch(error){if(!controller.signal.aborted){setMessage(error instanceof Error?error.message:'โหลดไม่ได้');setLoading(false);}}},250);
    return()=>{clearTimeout(timer);controller.abort();};
  },[q,offset,revision]);
  async function upload(file:File){
    if(file.size>8*1024*1024){setMessage('ไฟล์ต้องไม่เกิน 8 MB');return;}
    setBusy(true);setMessage('กำลังนำเข้า…');
    try{
      const response=await fetch('/api/formulary/import-xls',{method:'POST',credentials:'include',headers:{'Content-Type':'application/vnd.ms-excel'},body:file});
      const result=await response.json();if(!response.ok)throw Error(result.detail||'นำเข้าไม่ได้');
      setMessage(`นำเข้า ${result.imported} รายการ • ไม่ถือว่ามีของในคลังหรือเป็นยาทดแทนที่รับรอง`);setOffset(0);setRevision(value=>value+1);
    }catch(error){setMessage(error instanceof Error?error.message:'นำเข้าไม่ได้');}finally{setBusy(false);}
  }
  async function stock(item:Item,status:string){
    setBusy(true);try{
      const response=await fetch(`/api/formulary/${encodeURIComponent(item.code)}/stock`,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
      if(!response.ok)throw Error('บันทึกสถานะคลังไม่ได้');setRevision(value=>value+1);setMessage('บันทึกสถานะที่ผู้ตรวจระบุแล้ว ยังไม่เชื่อมยอดคงเหลือจริง');
    }catch(error){setMessage(error instanceof Error?error.message:'บันทึกไม่ได้');}finally{setBusy(false);}
  }
  return <section data-testid="hospital-formulary"><h2>รายการยาจากไฟล์โรงพยาบาล</h2><p>แยกจากคลังจำลอง 10 รายการและกฎขนาดยา ชื่อยาในไฟล์ไม่ยืนยันสถานะในบัญชี ยาคงเหลือ หรือความเหมาะสมในการใช้แทนกัน</p>
    {canManage&&<><label>นำเข้ารายการยา XLS<input type="file" accept=".xls" disabled={busy} onChange={e=>{const file=e.target.files?.[0];if(file)void upload(file);e.target.value='';}}/></label><p className="warning">ข้อมูลบน Vercel รุ่นนี้ยังเป็นฐานข้อมูลชั่วคราว อาจหายหรือไม่ตรงกันระหว่าง instances ต้องใช้ฐานข้อมูลถาวรก่อนใช้งานจริง ไม่อัปโหลดข้อมูลผู้ป่วย</p></>}
    <label>ค้นหายาโรงพยาบาล<input value={q} maxLength={200} onChange={e=>{setQ(e.target.value);setOffset(0);}} placeholder="ชื่อยา / ชื่อสามัญ / รหัสยา"/></label>
    <p>{loading?'กำลังค้นหา…':`พบ ${data?.matched??0} จาก ${data?.total??0} รายการ`}</p>{message&&<p>{message}</p>}
    {!loading&&data?.items.length===0&&<p>ยังไม่พบรายการ หากยังไม่ได้นำเข้า ให้เภสัชกรหรือผู้ดูแลนำเข้า XLS ที่ฐานความรู้ยา</p>}
    {!loading&&data?.items.map(item=><article key={item.code}><h3>{item.display_name}</h3><p>{item.code} · {item.generic_name||'ไม่มีชื่อสามัญในไฟล์'} · {item.strength||'ไม่ระบุความแรง'} · {item.dosage_form||'ไม่ระบุรูปแบบ'}</p>
      <p>สถานะคลัง: {stockLabel[item.stock_status]||'ยังไม่ทราบ'}{item.stock_checked_at&&` • ตรวจเมื่อ ${new Date(item.stock_checked_at).toLocaleString('th-TH',{timeZone:'Asia/Bangkok'})} (เวลาไทย)`}</p>
      <p>ช่องยาหมดในไฟล์: {item.source_stock_flag||'ว่าง — ไม่อนุมานว่ามีของ'} • ช่องอยู่ในบัญชี: {item.source_account_flag||'ว่าง — ยังไม่ยืนยัน'}</p>
      {canManage&&<label>สถานะที่เภสัชกร/ผู้ดูแลตรวจสอบ<select aria-label={`สถานะคลัง ${item.code}`} disabled={busy} value={item.stock_status} onChange={e=>void stock(item,e.target.value)}>{Object.entries(stockLabel).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>}
    </article>)}
    <button disabled={loading||offset===0} onClick={()=>setOffset(Math.max(0,offset-20))}>ก่อนหน้า</button><button disabled={loading||offset+20>=(data?.matched??0)} onClick={()=>setOffset(offset+20)}>ถัดไป</button>
  </section>;
}
