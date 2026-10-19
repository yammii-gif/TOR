'use client';
import {useState} from 'react';
type Row=Record<string,unknown>;
type Source={key:string;name:string;category:string;url:string;licensed:boolean;status:string;priority:number|null};
type Evidence={id:number;source_key:string;source_name:string;status:string;url:string;accessed_at:string;source_version:string|null;reviewer:string|null;content_hash:string|null;excerpt:string;error:string|null};
type Props={sources:Row[];records:Row[];drugs:Row[];canRetrieve:boolean;canReview:boolean;request:(path:string,body?:unknown)=>Promise<unknown>;safe:(action:()=>Promise<void>)=>Promise<void>;refresh:()=>Promise<void>};
export default function KnowledgeBase({sources,records,drugs,canRetrieve,canReview,request,safe,refresh}:Props){
  const [selectedDrug,setSelectedDrug]=useState(String(drugs[0]?.id||'')),[query,setQuery]=useState('assessment of kidney function'),[loading,setLoading]=useState(''),[conflictReason,setConflictReason]=useState('');
  const entries=records as unknown as Evidence[];
  async function retrieve(source:Source){setLoading(source.key);try{await request('/evidence/retrieve',{source_key:source.key,drug_id:source.key==='dailymed'?Number(selectedDrug):null,query});await refresh();}finally{setLoading('');}}
  return <><section><h2>ค่าไตและข้อมูลยา (DI): แหล่งอ้างอิงต้นฉบับ</h2>
    <p>ลำดับหลัก: Lexidrug/Micromedex เมื่อมีสิทธิ์ → FDA/DailyMed ตรวจฉลาก → KDIGO/NKF สนับสนุนการประเมินไต</p><p>ผลค้นหา DailyMed เป็นรายการเอกสาร ไม่ใช่ฉลากฉบับเต็ม ต้องเลือกและตรวจต้นฉบับก่อนเขียนกฎยา</p><p>ข้อมูลที่ดึงใหม่เป็น DRAFT ต้องตรวจต้นฉบับ เวอร์ชัน และทบทวนก่อนนำมาใช้ ไม่สร้างขนาดยาหรือเปิดใช้กฎยาอัตโนมัติ</p>
    <label>ยาสำหรับค้นหา DailyMed<select aria-label="ยาสำหรับค้นหา DailyMed" value={selectedDrug} onChange={e=>setSelectedDrug(e.target.value)}>{drugs.map(d=><option key={String(d.id)} value={String(d.id)}>{String(d.name)}</option>)}</select></label>
    <label>คำค้น UpToDate Search / PubMed<input value={query} maxLength={200} onChange={e=>setQuery(e.target.value)}/></label>
    <div className="source-grid">{(sources as unknown as Source[]).map(source=>{
      const latest=entries.find(e=>e.source_key===source.key);
      return <article className="source-card" key={source.key} data-testid={`source-${source.key}`}><h3>{source.name}</h3><p>{source.category}</p>{source.priority&&<p>ลำดับอ้างอิง renal dosing: {source.priority}</p>}<p className="badge">{latest?.status||source.status}</p>
        {source.key==='uptodate_search'&&<p>ค้นหาได้จากหน้าสาธารณะ การพบผลค้นหาไม่ได้ยืนยันสิทธิ์อ่านบทความเต็มหรือความถูกต้องของขนาดยา</p>}
        {source.licensed&&<p>LICENSE_REQUIRED — ต้องมีการเชื่อมต่อที่สถาบันและเจ้าของข้อมูลอนุญาต ยังไม่มีเนื้อหาที่ดึงแล้ว</p>}
        <p><a href={source.url} target="_blank" rel="noreferrer">เปิดแหล่งต้นฉบับ{source.licensed?'ผ่านบัญชีสถาบัน':''}</a></p>
        {canRetrieve&&<button disabled={!!loading||(source.key==='dailymed'&&!selectedDrug)} onClick={()=>safe(()=>retrieve(source))}>{loading===source.key?'กำลังตรวจการเข้าถึง…':source.licensed?'ตรวจสถานะสิทธิ์':'ดึงต้นฉบับเป็น DRAFT'}</button>}
      </article>;
    })}</div>
  </section><section><h2>ประวัติการเข้าถึงและหลักฐาน</h2>{!entries.length&&<p>ยังไม่มีต้นฉบับที่นำเข้า ไม่ถือว่าแหล่งข้อมูลถูกตรวจสอบแล้ว</p>}
    {canReview&&<label>รายละเอียดความขัดแย้งของแหล่งข้อมูล<input value={conflictReason} onChange={e=>setConflictReason(e.target.value)}/></label>}
    {entries.map(e=><article key={e.id} data-testid={`evidence-${e.id}`}><h3>{e.source_name} · {e.status}</h3><p>{new Date(e.accessed_at).toLocaleString('th-TH',{timeZone:'Asia/Bangkok'})} (เวลาไทย)</p>
      <p><a href={e.url} target="_blank" rel="noreferrer">{e.url}</a></p><p>เวอร์ชันต้นฉบับ: {e.source_version||'ยังไม่ยืนยัน'} • ผู้ทบทวน: {e.reviewer||'ยังไม่ทบทวน'}</p>
      {e.error&&<p className="warning">{e.error}</p>}
      {e.content_hash&&<><details><summary>ดูข้อความต้นฉบับบางส่วนและ checksum</summary><pre>{e.excerpt}</pre><p className="source-hash">SHA-256: {e.content_hash}</p></details><a href={`/api/evidence/${e.id}/raw`}>ดาวน์โหลดต้นฉบับที่เก็บไว้</a>
        {canReview&&<button disabled={!conflictReason.trim()} onClick={()=>safe(async()=>{await request(`/evidence/${e.id}/flag-conflict`,{reason:conflictReason});setConflictReason('');await refresh();})}>แจ้ง SOURCE_CONFLICT</button>}
      </>}
      <p>สถานะทางคลินิก: PENDING_CLINICAL_VALIDATION</p>
    </article>)}
  </section><section><h2>ทะเบียนยาเริ่มต้น 10 รายการ</h2>{drugs.map(d=><p key={String(d.id)}>{String(d.name)} — {String(d.status)} • คลังจำลอง: {String(d.stock_status)}{canReview&&<button onClick={()=>safe(async()=>{await request(`/rules/${d.id}/draft`,{});})}>สร้างกฎฉบับร่าง</button>}</p>)}</section></>;
}
