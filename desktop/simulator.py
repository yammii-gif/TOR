"""Local synthetic HOSxP-like screenshot OCR. No real window capture."""
import argparse, re, time
from datetime import datetime, timezone
from PIL import Image, ImageDraw
import pytesseract

def frame(patient='SYN-001'):
    image=Image.new('RGB',(1200,800),'white');d=ImageDraw.Draw(image)
    lines=['SYNTHETIC DATA',f'HN: {patient}','Age: 65','Weight: 60 kg','Sex: female','SCr: 1.5 mg/dL','eGFR: 38 mL/min/1.73m2','Lab: '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),'Diagnosis: Type 2 diabetes','Medication: Metformin','Dose: UNVERIFIED','Frequency: UNVERIFIED']
    d.multiline_text((35,30),'\n'.join(lines),fill='black',font_size=32,spacing=17)
    return image

def parse_text(text):
    patterns={'patient_id':r'HN:\s*(SYN-\d+)','age':r'Age:\s*(\d+)','weight_kg':r'Weight:\s*([\d.]+)\s*kg','sex':r'Sex:\s*(female|male)','scr':r'SCr:\s*([\d.]+)\s*mg/dL','egfr':r'eGFR:\s*([\d.]+)','collected_at':r'Lab:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})','diagnosis':r'Diagnosis:\s*([^\n]+)','medication':r'Medication:\s*([^\n]+)','dose':r'Dose:\s*([^\n]+)','frequency':r'Frequency:\s*([^\n]+)'}
    values={}
    for key,pattern in patterns.items():
        m=re.search(pattern,text,re.I)
        if m:values[key]=float(m.group(1)) if key in ['scr','egfr','weight_kg','age'] else m.group(1)
    if 'scr' in values:values['unit']='mg/dL'
    return values

def extract(image):
    data=pytesseract.image_to_data(image,output_type=pytesseract.Output.DICT)
    confidence=min((float(c) for t,c in zip(data['text'],data['conf']) if t.strip() and float(c)>=0),default=0)/100
    text=pytesseract.image_to_string(image)
    return {'status':'VERIFICATION_REQUIRED','fields':parse_text(text),'confidence':confidence,'clinical_recommendations_enabled':False,'retained_screenshot':False}

class SyntheticMonitor:
    def __init__(self,expected_patient_id='SYN-001',interval=2.5):
        if interval<2:raise ValueError('Minimum synthetic polling interval is 2 seconds')
        self.interval=interval;self.expected=expected_patient_id;self.running=False
    def start(self):self.running=True
    def pause(self):self.running=False
    def stop(self):self.running=False
    def process(self,image):
        if not self.running:return {'status':'STOPPED'}
        result=extract(image)
        if result['fields'].get('patient_id')!=self.expected:
            self.pause();result['reason']='PATIENT_IDENTITY_CHANGED'
        return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ocr',action='store_true');args=parser.parse_args()
    image=frame()
    if args.ocr:
        monitor=SyntheticMonitor();monitor.start();print(monitor.process(image));monitor.stop()
    else:print('Synthetic image generated in memory; use --ocr with local Tesseract installed')
