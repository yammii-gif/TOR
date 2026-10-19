"""Local, read-only ROI extraction. No network calls, disk output or dose decisions."""
import json
import math
import re
from pathlib import Path
import pytesseract

# Geometry only; no patient pixels or values are included in this profile.
PROFILE = {
    'id': 'hosxp-lab-strip-1395x224-v1',
    'size': (1395, 224),
    'regions': {
        'weight_kg': (476, 48, 524, 70),
        'height_cm': (580, 48, 626, 70),
        'scr': (764, 75, 814, 98),
        'egfr_reported': (868, 75, 918, 98),
    },
}
REQUIRED_CONTEXT = ('patient_id', 'age', 'sex', 'scr_unit', 'egfr_unit', 'collected_at')


def numeric_cell(text):
    """Reject OCR guesses such as O/0, commas and multiple numbers."""
    value = text.strip()
    if not re.fullmatch(r'(?:\d+(?:\.\d+)?|\.\d+)', value):
        return None
    number = float(value)
    return number if math.isfinite(number) and number > 0 else None


def ocr_cell(image):
    data = pytesseract.image_to_data(
        image.resize((image.width * 4, image.height * 4)),
        config='--psm 7', output_type=pytesseract.Output.DICT,
    )
    tokens = [(word.strip(), float(conf)) for word, conf in zip(data['text'], data['conf']) if word.strip()]
    return ' '.join(word for word, _ in tokens), min((max(0, conf) for _, conf in tokens), default=0) / 100


def extract_regions(image, profile=PROFILE, reader=ocr_cell):
    if image.size != tuple(profile['size']):
        return {'status': 'VERIFICATION_REQUIRED', 'reason': 'LAYOUT_MISMATCH',
                'fields': {}, 'clinical_recommendations_enabled': False}
    fields = {}
    for key, box in profile['regions'].items():
        crop = image.crop(tuple(box))
        try:
            text, confidence = reader(crop)
        finally:
            crop.close()
        value = numeric_cell(text)
        fields[key] = {'value': value, 'confidence': confidence,
                       'status': 'VERIFICATION_REQUIRED' if value is None or confidence < .95 else 'OCR_CANDIDATE',
                       'source': profile['id']}
    return {'status': 'VERIFICATION_REQUIRED', 'fields': fields,
            'missing_context': list(REQUIRED_CONTEXT),
            'reason': 'PATIENT_UNIT_AND_LAB_TIME_NOT_IN_THIS_REGION',
            'clinical_recommendations_enabled': False, 'retained_screenshot': False}


def main():
    # Intentionally no server, upload, telemetry, clipboard or save/export button.
    import tkinter as tk
    from tkinter import filedialog
    from PIL import Image
    root = tk.Tk()
    root.title('Renal Smart — Local Lab Reader (ต้องตรวจยืนยัน)')
    tk.Label(root, text='อ่านภาพในเครื่องเท่านั้น • ไม่ส่งขึ้นเว็บ • ไม่ยืนยันตัวผู้ป่วยหรือสั่งยา', wraplength=700).pack()
    output = tk.Text(root, width=85, height=28)
    output.pack()

    def read():
        path = filedialog.askopenfilename(filetypes=[('PNG image', '*.png')])
        if not path:
            return
        output.delete('1.0', tk.END)
        try:
            with Image.open(Path(path)) as image:
                result = extract_regions(image)
            output.insert(tk.END, json.dumps(result, ensure_ascii=False, indent=2))
        except Exception:
            # Never print image paths, OCR text or patient values in logs.
            output.insert(tk.END, 'อ่านภาพไม่ได้: ตรวจขนาดภาพ 1395×224, ตำแหน่งช่อง และการติดตั้ง Tesseract')

    tk.Button(root, text='เลือกภาพเฉพาะแถบแล็บเพื่ออ่านในเครื่อง', command=read).pack()
    tk.Button(root, text='ล้างข้อมูล', command=lambda: output.delete('1.0', tk.END)).pack()
    root.mainloop()


if __name__ == '__main__':
    main()
