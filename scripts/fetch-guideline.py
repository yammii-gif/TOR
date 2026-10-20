#!/usr/bin/env python3
"""Download a public guideline on an authorized network. No login/proxy bypass."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.guidelines import fetch_pdf,parse_pdf

parser=argparse.ArgumentParser(description='ดาวน์โหลด PDF จาก KDIGO / NICE / NKF / NIDDK โดยใช้สิทธิ์เครือข่ายปกติของเครื่อง')
parser.add_argument('url');parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
try:
    content,url=fetch_pdf(args.url);pages=parse_pdf(content)
except Exception:
    print('FETCH_FAILED: ไม่ได้ PDF ต้นฉบับ ตรวจเครือข่าย สิทธิ์ และ URL ไม่ข้ามการปิดกั้น',file=sys.stderr)
    raise SystemExit(2)
digest=hashlib.sha256(content).hexdigest()
args.output.mkdir(parents=True,exist_ok=True)
(args.output/f'{digest}.pdf').write_bytes(content)
(args.output/f'{digest}.json').write_text(json.dumps({'url':url,'sha256':digest,'pages':len(pages),
    'retrieved_at':datetime.now(timezone.utc).isoformat(),'status':'DRAFT','reviewer':None},ensure_ascii=False,indent=2))
print(f'PDF_DOWNLOADED: {len(pages)} pages; SHA-256 {digest}; ยังไม่ใช่กฎคลินิกที่รับรอง')
