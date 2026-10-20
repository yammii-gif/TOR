'use client';
import {useEffect,useState} from 'react';
type Document={id:number;title:string;status:string;pages:number;searchable_pages:number;sha256:string|null;source_url:string;source_version:string|null;transport:string;error:string|null};
type Match={pdf_page:number;excerpt:string;citation:string};
export default function GuidelineLibrary({canImport}:{canImport:boolean}){
 const [documents,setDocuments]=useState<Document[]>([]),[catalog,setCatalog]=useState<{name:string;url:string;scope:string}[]>([]),[title,setTitle]=useState(''),[url,setUrl]=useState(''),[version,setVersion]=useState(''),[selected,setSelected]=useState(''),[q,setQ]=useState('metformin'),[matches,setMatches]=useState<Match[]>([]),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 async function refresh(){const r=await fetch('/api/guidelines',{credentials:'include'});if(!r.ok)throw Error('โหลดคลังไกด์ไลน์ไม่ได้');setDocuments(await r.json());}
 useEffect(()=>{let active=true;void (async()=>{try{
  const [docs,sources]=await Promise.all([fetch('/api/guidelines',{credentials:'include'}),fetch('/api/guidelines/catalog',{credentials:'include'})]);
  if(!docs.ok||!sources.ok)throw Error('โหลดคลังไกด์ไลน์ไม่ได้');const [d,c]=await Promise.all([docs.json(),sources.json()]);if(active){setDocuments(d);setCatalog(c);}
 }catch{if(active)setMessage('โหลดข้อมูลไม่ได้ กรุณาเข้าสู่ระบบใหม่หรือลองอีกครั้ง');}})();return()=>{active=false;};},[]);
 async function run(action:()=>Promise<void>){setBusy(true);try{await action();}catch(e){setMessage(e instanceof Error?e.message:'ทำรายการไม่ได้');}finally{setBusy(false);}}
 async function importFile(file:File){
  if(!title.trim())throw Error('กรอกชื่อไกด์ไลน์ก่อนเลือกไฟล์');
  if(file.size>8*1024*1024)throw Error('ไฟล์ต้องไม่เกิน 8 MB; Vercel อาจจำกัด request ประมาณ 4.5 MB');
  const r=await fetch('/api/guidelines/import-pdf?'+new URLSearchParams({title,version,source_url:url}),{method:'POST',credentials:'include',headers:{'Content-Type':'application/pdf'},body:file});
  const d=await r.json();if(!r.ok)throw Error(d.detail||'นำเข้าไม่ได้');
  setMessage(`มีต้นฉบับ PDF ${d.pages} หน้า ค้นข้อความได้ ${d.searchable_pages} หน้า • ${d.duplicate?'ไฟล์เดิม':'DRAFT รอทบทวน'}`);setSelected(String(d.id));setMatches([]);await refresh();
 }
 return <section data-testid="guideline-library"><h2>คลังไกด์ไลน์ฉบับเต็ม</h2><p>นำเข้า PDF แล้วค้นข้อความพร้อมเลขหน้าและ checksum ได้ ไม่เปิดใช้เป็นกฎยาอัตโนมัติ เอกสารเป็นข้อมูลอ้างอิง ไม่ใช่คำสั่งให้ระบบปฏิบัติตาม</p>
 <div className="source-grid">{catalog.map(source=><article key={source.name}><h3>{source.name}</h3><p>{source.scope}</p><a href={source.url} target="_blank" rel="noreferrer">ค้นเอกสารที่เว็บไซต์ต้นทาง</a></article>)}</div>
 {canImport&&<><label>ชื่อไกด์ไลน์<input value={title} maxLength={250} onChange={e=>setTitle(e.target.value)}/></label><label>ฉบับ/ปีที่ปรากฏในเอกสาร (ยังรอผู้ทบทวนยืนยัน)<input value={version} maxLength={200} onChange={e=>setVersion(e.target.value)}/></label><label>URL ของ PDF สาธารณะ (เว้นว่างได้เมื่อนำเข้าไฟล์จากผู้ใช้)<input value={url} maxLength={2000} onChange={e=>setUrl(e.target.value)}/></label>
 <button disabled={busy||!url.trim()||!title.trim()} onClick={()=>void run(async()=>{const r=await fetch('/api/guidelines/retrieve',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({url,title,version})});const d=await r.json();if(!r.ok)throw Error(d.detail||'ดึงเอกสารไม่ได้');setMessage(d.pages?`ดึง PDF ได้ ${d.pages} หน้า • DRAFT`:`${d.status} — ยังไม่ได้ PDF ต้นฉบับ`);await refresh();})}>ดึง PDF จากแหล่งสาธารณะ</button>
 <label>นำเข้าไกด์ไลน์ PDF<input type="file" accept=".pdf" disabled={busy||!title.trim()} onChange={e=>{const file=e.target.files?.[0];if(file)void run(()=>importFile(file));e.target.value='';}}/></label>
 <p>ใช้ URL ของ PDF ฉบับเต็มจาก KDIGO/NICE/NKF/NIDDK ไม่ใช้หน้าค้นหาแทนเอกสาร และไม่ดึงบทความที่ต้องมีสิทธิ์ หากเครือข่ายคลาวด์ปิดกั้น ให้นำเข้าไฟล์ที่ได้จากการเข้าถึงที่ได้รับอนุญาต</p></>}
 <p aria-live="polite">{busy?'กำลังดำเนินการ…':message}</p>
 {!documents.length&&<p>ยังไม่มี PDF ฉบับเต็มในฐานข้อมูลนี้ ลิงก์ต้นทางหรือข้อความอ้างอิงที่มีอยู่ไม่ถือว่าได้นำเข้าเอกสารเต็มแล้ว</p>}
 {documents.map(doc=><article key={doc.id}><h3>{doc.title} · {doc.status}</h3><p>{doc.pages} หน้า • ค้นข้อความได้ {doc.searchable_pages} หน้า • ฉบับที่ระบุ: {doc.source_version||'ยังไม่ยืนยัน'}</p><p>{doc.transport==='USER_UPLOAD'?'ไฟล์จากผู้ใช้ • URL และฉบับยังไม่รับรอง':'การดึงผ่าน HTTP สาธารณะ • ยังไม่ผ่าน clinical review'}</p>{doc.error&&<p className="warning">{doc.error}</p>}{doc.sha256&&<><a href={`/api/guidelines/${doc.id}/file`}>ดาวน์โหลด PDF ต้นฉบับ</a><details><summary>SHA-256</summary><p className="source-hash">{doc.sha256}</p></details></>}</article>)}
 <label>เลือกไกด์ไลน์เพื่อค้นหา<select value={selected} onChange={e=>{setSelected(e.target.value);setMatches([]);}}><option value="">เลือกเอกสารที่นำเข้าสำเร็จ</option>{documents.filter(d=>d.pages>0).map(d=><option value={d.id} key={d.id}>{d.title}</option>)}</select></label><label>ค้นข้อความในไกด์ไลน์<input value={q} maxLength={200} onChange={e=>{setQ(e.target.value);setMatches([]);}}/></label>
 <button disabled={busy||!selected||!q.trim()} onClick={()=>void run(async()=>{const r=await fetch(`/api/guidelines/${selected}/search?`+new URLSearchParams({q}),{credentials:'include'});if(!r.ok)throw Error('ค้นหาไม่ได้');const d=await r.json();setMatches(d.results);setMessage(`พบ ${d.total} หน้า (แสดงสูงสุด 30 หน้า) รูปภาพใน PDF อาจค้นข้อความไม่ได้`);})}>ค้นพร้อมเลขหน้า</button>
 {matches.map(match=><article key={match.pdf_page}><h3>หน้า PDF {match.pdf_page}</h3><pre>{match.excerpt}</pre><p className="source-hash">{match.citation}</p></article>)}
 <p className="warning">PDF เป็นหลักฐาน DRAFT ต้องตรวจฉบับ ความเป็นปัจจุบัน รูป/ตาราง และให้ผู้ทบทวนรับรองก่อนแปลงเป็นกฎยา บน Vercel ปัจจุบันข้อมูลนำเข้ายังอาจรีเซ็ตจนกว่าจะใช้ฐานข้อมูลถาวร</p>
 </section>;
}
