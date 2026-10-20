'use client';
import {apiFetch} from './api-client';
import {useEffect,useState} from 'react';
type Row=Record<string,unknown>;
type Finding={drug:string;section:string;pdf_pages:number[];printed_pages:number[];exact_excerpt:string;limitation:string;comparison_value:number|null;comparison_basis:string;matched_band:{source_statement:string}|null;source:{title:string;version_note:string;sha256:string}};
type Assessment={decision:{code:string;label:string;reason:string;actionable:boolean};alternatives_reason:string;document_findings:Finding[]};

export default function MedicationAssessment({patient,drug,indication}:{patient:Row;drug:string;indication:string}){
  const input=JSON.stringify({patient,drug,indication});
  const [state,setState]=useState<{input:string;data?:Assessment;error?:string}>({input:''});
  useEffect(()=>{
    const controller=new AbortController();
    const timer=setTimeout(async()=>{
      try{
        const response=await apiFetch('/api/assess',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:input,signal:controller.signal});
        const data=await response.json();
        if(!response.ok)throw Error('ข้อมูลไม่ครบหรือไม่ผ่านการตรวจสอบ กรุณาตรวจอายุ น้ำหนัก SCr หน่วย และเวลาแล็บ');
        if(!controller.signal.aborted)setState({input,data});
      }catch(error){if(!controller.signal.aborted)setState({input,error:error instanceof Error?error.message:'ประเมินไม่ได้'});}
    },350);
    return ()=>{clearTimeout(timer);controller.abort();};
  },[input]);
  const current=state.input===input;
  const assessment=current?state.data:undefined;
  const styles:Record<string,{className:string;label:string}>={CONTINUE:{className:'decision-green',label:'ใช้ยาเดิมต่อได้'},ADJUST_DOSE:{className:'decision-yellow',label:'ปรับขนาดยา'},CHANGE_DRUG:{className:'decision-red',label:'เปลี่ยนยา'},REVIEW_REQUIRED:{className:'decision-gray',label:'ยังสรุปไม่ได้ — ต้องทบทวน'}};
  const verdict=assessment?.decision.actionable?styles[assessment.decision.code]||styles.REVIEW_REQUIRED:styles.REVIEW_REQUIRED;
  return <div className="medication-assessment" data-testid="medication-assessment" aria-live="polite">
    <h3>สรุปความเหมาะสมของยา: {drug||'ยังไม่ระบุยา'}</h3>
    <p className="muted">ความหมายของสี</p><div className="decision-legend" aria-label="ประเภทผลประเมิน"><span className="decision-green">✓ ใช้ยาเดิมต่อได้</span><span className="decision-yellow">! ปรับขนาดยา</span><span className="decision-red">✕ เปลี่ยนยา</span><span className="decision-gray">? ยังสรุปไม่ได้</span></div>
    <div className={`decision-banner ${verdict.className}`} data-testid="medication-verdict"><strong>{verdict.label}</strong><p>{!current?'กำลังประเมินข้อมูลชุดล่าสุด…':state.error||assessment?.decision.reason||'กำลังประเมิน…'}</p></div>
    <p>ประเมินอัตโนมัติเมื่อเปลี่ยนยา ข้อบ่งใช้ หรือข้อมูลไต ผลเก่าจะถูกซ่อนทันที</p>
    <h3>ยาทางเลือก</h3><p>{assessment?.alternatives_reason||'ยังไม่มีทางเลือกที่ยืนยันสำหรับข้อมูลชุดนี้'}</p>
    <p className="warning">NO_VALIDATED_ALTERNATIVE — CLINICAL REVIEW REQUIRED</p>
    {assessment?.document_findings.map((finding,i)=><details key={i} open data-testid="document-finding"><summary>เกณฑ์ที่พบในเอกสารแนบ — รอรับรอง ไม่ใช่คำแนะนำสั่งยา</summary>
      <p>{finding.source.title}</p><p>หน้าเอกสาร {finding.printed_pages.join('–')} · หน้า PDF {finding.pdf_pages.join('–')} · {finding.section}</p>
      <p>{finding.comparison_basis}: {finding.comparison_value??'ไม่ได้ระบุ'} mL/min/1.73m²</p>
      <p><strong>{finding.matched_band?.source_statement||'ไม่มี eGFR จากแล็บให้เทียบเกณฑ์ ไม่ใช้ CrCl แทน'}</strong></p>
      <blockquote>{finding.exact_excerpt}</blockquote><p>{finding.source.version_note}</p><p>{finding.limitation}</p>
      <details><summary>ตรวจสอบ SHA-256 ของเอกสารแนบ</summary><p className="source-hash">{finding.source.sha256}</p></details>
    </details>)}
  </div>;
}
