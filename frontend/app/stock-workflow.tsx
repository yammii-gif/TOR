'use client';
import {useState} from 'react';

export type StockDrug={id:number;name:string;stock_status:string;clinical_status:string};
type Row=Record<string,unknown>;
type Alternative={id:number;drug:string;stock_status:string;indication:string;rationale:string;status:string;proposed_by:string};
type RecordRow={id:number;patient:string;drug:string;proposal:string;reason:string;status:string;source_snapshot:Row;stock_alternatives:Alternative[]};
type Actions={request:(path:string,body?:unknown)=>Promise<unknown>;safe:(action:()=>Promise<void>)=>Promise<void>;refresh:()=>Promise<void>};
const pending=['WAITING_STOCK_ALTERNATIVE','ALTERNATIVE_PROPOSED'];
const labels:Record<string,string>={PHYSICIAN_FINALIZED:'แพทย์ยืนยันการตัดสินใจแล้ว',WAITING_STOCK_ALTERNATIVE:'ยาขาดคลัง • รอเภสัชกรเสนอทางเลือก',ALTERNATIVE_PROPOSED:'มีข้อเสนอจากเภสัชกร • รอแพทย์เลือก',REPLACED_BY_PHYSICIAN:'แพทย์เปลี่ยนเป็นรายการใหม่แล้ว',SUBMITTED:'รายการเดิมจาก workflow ก่อนหน้า'};

function AlternativeChoice({record,alternative,request,safe,refresh}:Actions&{record:RecordRow;alternative:Alternative}){
  const [proposal,setProposal]=useState(''),[reason,setReason]=useState(''),[override,setOverride]=useState(false);
  async function decide(action:string){await request(`/prescriptions/${record.id}/stock-alternatives/${alternative.id}/decision`,{action,proposal,reason,override});await refresh();}
  return <div className="stock-offer" data-testid={`stock-alternative-${alternative.id}`}>
    <h3>{alternative.drug} <span className="badge">{alternative.stock_status==='IN_STOCK'?'มีในคลังจำลอง':'ขาดคลังแล้ว'}</span></h3>
    <p>ผู้เสนอ: {alternative.proposed_by} • ข้อบ่งใช้: {alternative.indication}</p><p>{alternative.rationale}</p>
    <p className="warning">ข้อเสนอโดยเภสัชกรเพื่อให้แพทย์ทบทวน ยังไม่ใช่ยาทดแทนที่ระบบรับรอง ไม่มีขนาดยาอัตโนมัติ</p>
    <label>ข้อเสนอใหม่ของแพทย์<textarea value={proposal} onChange={e=>setProposal(e.target.value)}/></label>
    <label>เหตุผลการเลือกหรือไม่เลือก<input value={reason} onChange={e=>setReason(e.target.value)}/></label>
    <label><input type="checkbox" checked={override} onChange={e=>setOverride(e.target.checked)}/>แพทย์ทบทวนข้อจำกัดของข้อมูลไตและยืนยัน Override พร้อมเหตุผล</label>
    <button disabled={!proposal.trim()||!reason.trim()||alternative.stock_status!=='IN_STOCK'} onClick={()=>safe(()=>decide('ACCEPT'))}>เลือกยานี้และยืนยันโดยแพทย์</button>
    <button disabled={!reason.trim()} onClick={()=>safe(()=>decide('DECLINE'))}>ไม่เลือกข้อเสนอนี้</button>
  </div>;
}

export function PhysicianDecisions({records,request,safe,refresh}:Actions&{records:Row[]}){
  const list=records as unknown as RecordRow[];
  return <section><h2>การตัดสินใจของแพทย์</h2><p>ยาที่มีในคลังจำลองบันทึกการตัดสินใจได้ทันที เภสัชกรรับงานเมื่อยาขาดคลัง ไม่มีการเขียนกลับ HOSxP</p>
    {!list.length&&<p>ยังไม่มีรายการ</p>}
    {[...list].reverse().map(record=><article key={record.id} data-testid={`physician-record-${record.id}`}>
      <h3>#{record.id} · {record.patient} · {record.drug}</h3>
      <p className={`workflow-status ${record.status==='PHYSICIAN_FINALIZED'?'done':'pending'}`}>{labels[record.status]||record.status}</p>
      <p>ข้อเสนอแพทย์: {record.proposal}</p>{record.reason&&<p>เหตุผล: {record.reason}</p>}
      {pending.includes(record.status)&&record.stock_alternatives.filter(a=>a.status==='PROPOSED').map(a=><AlternativeChoice key={a.id} record={record} alternative={a} request={request} safe={safe} refresh={refresh}/>)}
      <details><summary>ข้อมูลต้นทางของรายการนี้</summary><pre>{JSON.stringify(record.source_snapshot,null,2)}</pre></details>
    </article>)}
  </section>;
}

function StockOffer({record,inventory,request,safe,refresh}:Actions&{record:RecordRow;inventory:StockDrug[]}){
  const [selected,setSelected]=useState(''),[indication,setIndication]=useState(String(record.source_snapshot.diagnosis||'')),[rationale,setRationale]=useState('');
  const available=inventory.filter(d=>d.stock_status==='IN_STOCK'&&d.name!==record.drug);
  return <div><p className="warning">รายชื่อนี้ระบุเฉพาะการมีในคลังจำลอง เภสัชกรต้องทบทวนข้อบ่งใช้ แพ้ยา ปฏิกิริยาระหว่างยา และข้อมูลไต ก่อนเสนอให้แพทย์ตัดสินใจ</p>
    <label>ยาที่มีในคลังจำลอง<select aria-label="ยาที่มีในคลังจำลอง" value={selected} onChange={e=>setSelected(e.target.value)}><option value="">เลือกยาที่จะเสนอ</option>{available.map(d=><option key={d.id} value={d.id}>{d.name} • รอรับรองทางคลินิก</option>)}</select></label>
    <label>ข้อบ่งใช้ที่เภสัชกรทบทวน<input value={indication} onChange={e=>setIndication(e.target.value)}/></label>
    <label>เหตุผลและข้อควรพิจารณาของเภสัชกร<textarea value={rationale} onChange={e=>setRationale(e.target.value)}/></label>
    <button disabled={!selected||!indication.trim()||rationale.trim().length<10} onClick={()=>safe(async()=>{await request(`/prescriptions/${record.id}/stock-alternatives`,{drug_id:Number(selected),indication,rationale});setSelected('');setRationale('');await refresh();})}>เสนอทางเลือกให้แพทย์</button>
  </div>;
}

export function PharmacyStock({records,inventory,canPropose,request,safe,refresh}:Actions&{records:Row[];inventory:StockDrug[];canPropose:boolean}){
  const list=records as unknown as RecordRow[];
  const queue=list.filter(r=>pending.includes(r.status));
  return <><section><h2>คลังยาจำลอง</h2><p>SYNTHETIC INVENTORY • ใช้สถานะมี/ขาดสำหรับเดโม ยังไม่เชื่อมคลังยาจริงของโรงพยาบาล</p>
    <div className="inventory-table">{inventory.map(d=><div key={d.id} className="inventory-row" data-testid={`inventory-${d.id}`}><strong>{d.name}</strong><span>{d.stock_status==='IN_STOCK'?'มีในคลังจำลอง':'ขาดคลังจำลอง'}</span><button onClick={()=>safe(async()=>{await request(`/inventory/${d.id}`,{status:d.stock_status==='IN_STOCK'?'OUT_OF_STOCK':'IN_STOCK'});await refresh();})}>{d.stock_status==='IN_STOCK'?'ทำเครื่องหมายยาขาด':'ทำเครื่องหมายมีในคลัง'}</button></div>)}</div>
  </section><section><h2>งานเภสัชกรเฉพาะยาขาดคลัง ({queue.length})</h2>
    {!queue.length&&<p>ไม่มียาขาดคลังที่รอเสนอทางเลือก</p>}
    {queue.map(r=><article key={r.id} data-testid={`stock-request-${r.id}`}><h3>#{r.id} · {r.patient} · {r.drug}</h3><p>{labels[r.status]}</p><p>ข้อเสนอแพทย์เดิม: {r.proposal}</p><details><summary>ดูข้อมูลผู้ป่วย แล็บ และการคำนวณต้นทาง</summary><pre>{JSON.stringify(r.source_snapshot,null,2)}</pre></details>
      {r.stock_alternatives.map(a=><p key={a.id}>เสนอ {a.drug}: {a.status} — {a.rationale}</p>)}
      {canPropose&&<StockOffer record={r} inventory={inventory} request={request} safe={safe} refresh={refresh}/>}
    </article>)}
  </section><section><details><summary>ประวัติการตัดสินใจทั้งหมด (อ่านเพื่อติดตาม)</summary>{list.map(r=><p key={r.id}>#{r.id} · {r.drug} · {labels[r.status]||r.status}</p>)}</details></section></>;
}
