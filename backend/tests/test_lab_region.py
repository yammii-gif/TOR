"""Synthetic fixtures only: no supplied clinical screenshot retained."""
import importlib.util
from pathlib import Path
from PIL import Image

spec = importlib.util.spec_from_file_location('lab_region', Path(__file__).parents[2] / 'desktop' / 'lab_region.py')
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def test_ambiguous_ocr_never_normalizes_guessed_digits():
    for text in ('1.O4', '1,04', '1.0 4', '-1', 'NaN', '', '0'):
        assert lab.numeric_cell(text) is None
    assert lab.numeric_cell(' 1.25 ') == 1.25


def test_lab_strip_never_implies_identity_units_or_timestamp():
    image = Image.new('RGB', lab.PROFILE['size'], 'white')
    cells = iter([('62', .99), ('165', .99), ('1.25', .99), ('58.7', .99)])
    result = lab.extract_regions(image, reader=lambda _: next(cells))
    assert result['fields']['scr']['value'] == 1.25
    assert result['fields']['egfr_reported']['value'] == 58.7
    assert 'scr_unit' in result['missing_context'] and 'patient_id' in result['missing_context']
    assert 'collected_at' in result['missing_context']
    assert result['status'] == 'VERIFICATION_REQUIRED'
    assert result['clinical_recommendations_enabled'] is False
    assert result['retained_screenshot'] is False


def test_layout_mismatch_does_not_ocr_and_low_confidence_is_blocked():
    def forbidden(_):
        raise AssertionError('Wrong layout must not be OCRed')
    assert lab.extract_regions(Image.new('RGB', (900, 200)), reader=forbidden)['reason'] == 'LAYOUT_MISMATCH'
    result = lab.extract_regions(Image.new('RGB', lab.PROFILE['size']), reader=lambda _: ('1.2', .5))
    assert all(f['status'] == 'VERIFICATION_REQUIRED' for f in result['fields'].values())
