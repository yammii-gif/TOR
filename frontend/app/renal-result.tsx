type Result = Record<string, unknown>;

export default function RenalResult({ result }: { result: Result | null }) {
  if (!result) return <p>กรอกข้อมูลจำลองแล้วกดคำนวณ เพื่อดู CrCl และ eGFR จากข้อมูลชุดนี้</p>;
  const calculation = result.calculation && typeof result.calculation === 'object'
    ? result.calculation as Result : result;
  const ready = typeof calculation.crcl === 'number' && typeof calculation.egfr === 'number' && typeof calculation.egfr_method === 'string';
  const parameters = calculation.egfr_parameters && typeof calculation.egfr_parameters === 'object'
    ? calculation.egfr_parameters as Result : {};
  return <>
    {ready ? <>
      <p className="badge">ผลคำนวณจากข้อมูลที่กรอก • ข้อมูลจำลอง</p>
      <div className="renal-values">
        <div><span>CrCl · Cockcroft–Gault</span><strong data-testid="crcl-result">{Number(calculation.crcl).toFixed(2)}</strong><span>mL/min</span></div>
        <div><span>eGFR · CKD-EPI 2021</span><strong data-testid="egfr-result">{Number(calculation.egfr).toFixed(2)}</strong><span>mL/min/1.73m²</span></div>
      </div>
      <p>SCr ที่ใช้ในสูตร: {String(calculation.scr_mg_dl)} mg/dL</p>
      <p className="calculation">{String(calculation.crcl_explanation)}</p>
      <p>eGFR จากแล็บที่กรอก: {typeof calculation.egfr_reported === 'number' ? `${calculation.egfr_reported} mL/min/1.73m²` : 'ไม่ได้ระบุ'}</p>
      <div className="warning">CrCl และ eGFR เป็นค่าประมาณคนละวิธีและใช้หน่วยต่างกัน ต้องเลือกตามข้อกำหนดของกฎยา ยังไม่มีคำแนะนำขนาดยาที่ได้รับอนุมัติ</div>
    </> : <div className="warning" role="alert">
      <strong>{calculation.status === 'VERIFICATION_REQUIRED' ? 'ต้องตรวจสอบข้อมูลก่อนคำนวณ' : 'ต้องทบทวนโดยผู้เชี่ยวชาญ'}</strong>
      <p>{String(calculation.reason || result.reason || 'ยังไม่มีข้อมูลหรือกฎที่ผ่านการตรวจสอบสำหรับกรณีนี้')}</p>
    </div>}
    {result.status === 'PENDING_CLINICAL_VALIDATION' && <p>การประเมินยา: รอการรับรองทางคลินิก</p>}
    <details><summary>ดูสูตร หลักฐาน และข้อมูลสำหรับตรวจสอบ</summary>
      {ready && <><p>{String(calculation.formula)}</p><p>{String(calculation.egfr_formula)}</p><p>κ = {String(parameters.kappa)}, α = {String(parameters.alpha)}</p></>}
      <p><a href="https://doi.org/10.1159/000180580" target="_blank" rel="noreferrer">Cockcroft & Gault, Nephron 1976;16:31–41</a></p>
      <p><a href="https://doi.org/10.1056/NEJMoa2102953" target="_blank" rel="noreferrer">Inker et al., NEJM 2021 — CKD-EPI race-free equation</a></p>
      <p>สูตรยังรอการทบทวนของสถาบันสำหรับการใช้งานจริง ไม่มีการเปิดใช้กฎขนาดยา</p>
      <pre>{JSON.stringify(result, null, 2)}</pre>
    </details>
  </>;
}
