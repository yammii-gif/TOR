'use client';
import {useEffect,useState} from 'react';
import {apiFetch} from './api-client';
type Staff={id:number;username:string;role:string;enabled:boolean};
export default function StaffUsers(){
 const [users,setUsers]=useState<Staff[]>([]),[username,setUsername]=useState(''),[password,setPassword]=useState(''),[role,setRole]=useState('physician'),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 async function refresh(){const r=await apiFetch('/api/admin/users');if(!r.ok)throw Error('โหลดบัญชีไม่ได้');setUsers(await r.json());}
 useEffect(()=>{void refresh().catch(()=>setMessage('ไม่สามารถโหลดบัญชีผู้ใช้ได้'));},[]);
 async function run(action:()=>Promise<void>){setBusy(true);try{await action();await refresh();setMessage('บันทึกแล้ว การเปลี่ยนบัญชีจะเพิกถอนsessionเดิมของบัญชีนั้น');}catch(e){setMessage(e instanceof Error?e.message:'บันทึกไม่ได้');}finally{setBusy(false);}}
 async function change(user:Staff,body:Record<string,unknown>){const r=await apiFetch(`/api/admin/users/${user.id}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw Error('เปลี่ยนบัญชีไม่ได้ ต้องเหลือผู้ดูแลที่เปิดใช้งานอย่างน้อยหนึ่งบัญชี');}
 return <section><h2>บัญชีผู้ใช้รายบุคคล</h2><p>บทบาทกำหนดโดยผู้ดูแล ไม่ให้เลือกสิทธิ์ตอนเข้าสู่ระบบ การปิดบัญชี/เปลี่ยนสิทธิ์/เปลี่ยนรหัสผ่านจะเพิกถอนsessionเดิม</p>
 <label>ชื่อบัญชีใหม่<input value={username} maxLength={64} autoComplete="off" onChange={e=>setUsername(e.target.value)}/></label><label>รหัสผ่านเริ่มต้น (อย่างน้อย12ตัวอักษร)<input type="password" autoComplete="new-password" maxLength={256} value={password} onChange={e=>setPassword(e.target.value)}/></label><label>สิทธิ์บัญชีใหม่<select aria-label="สิทธิ์บัญชีใหม่" value={role} onChange={e=>setRole(e.target.value)}>{['physician','pharmacist','admin','researcher'].map(value=><option key={value}>{value}</option>)}</select></label>
 <button disabled={busy||!username||password.length<12} onClick={()=>void run(async()=>{const r=await apiFetch('/api/admin/users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password,role})});setPassword('');if(!r.ok)throw Error('สร้างบัญชีไม่ได้ ตรวจชื่อซ้ำและรูปแบบชื่อ');setUsername('');})}>สร้างบัญชีรายบุคคล</button><p aria-live="polite">{message}</p>
 {users.map(user=><article key={user.id}><h3>{user.username}</h3><p>{user.role} · {user.enabled?'เปิดใช้งาน':'ปิดใช้งาน'}</p><label>เปลี่ยนสิทธิ์ {user.username}<select aria-label={`เปลี่ยนสิทธิ์ ${user.username}`} disabled={busy} value={user.role} onChange={e=>void run(()=>change(user,{role:e.target.value}))}>{['physician','pharmacist','admin','researcher'].map(value=><option key={value}>{value}</option>)}</select></label><button disabled={busy} onClick={()=>void run(()=>change(user,{enabled:!user.enabled}))}>{user.enabled?'ปิดบัญชี':'เปิดบัญชี'} {user.username}</button></article>)}
 <p>การตั้งรหัสผ่านใหม่ทำผ่านคำสั่งผู้ดูแลบนเครื่องที่ปลอดภัย ตามคู่มือติดตั้ง ไม่ส่งรหัสผ่านผ่านแชตหรืออีเมลทั่วไป</p>
 </section>;
}
