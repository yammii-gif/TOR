import pytest
from datetime import datetime, timezone, timedelta
from test_safety import db, client, patient
from app.medication_assessment import assess_medication


@pytest.mark.parametrize('egfr,category',[(0,'AVOID'),(29.999,'AVOID'),(30,'ADJUST'),(44.999,'ADJUST'),(45,'CONDITIONAL'),(59.999,'CONDITIONAL'),(60,'RENAL_ONLY'),(90,'RENAL_ONLY')])
def test_document_bands_never_become_approved_patient_decisions(egfr,category):
    result=assess_medication(patient(egfr=egfr),'Metformin','type 2 diabetes')
    assert result['decision']['code']=='REVIEW_REQUIRED'
    assert result['decision']['actionable'] is False
    assert result['decision']['dose'] is None and result['alternatives']==[]
    finding=result['document_findings'][0]
    assert finding['matched_band']['source_category']==category
    assert finding['comparison_value']==egfr
    assert finding['actionable'] is False and finding['dose'] is None
    assert finding['source']['status']=='PENDING_CLINICAL_VALIDATION'
    assert finding['pdf_pages']==[53,54] and finding['printed_pages']==[37,38]
    assert finding['source']['reviewed_by_clinician'] is None


def test_no_rounding_crcl_substitution_or_measure_guess():
    result=assess_medication(patient(egfr=None),'Metformin','type 2 diabetes')
    assert result['calculation']['crcl']>0
    assert result['document_findings'][0]['matched_band'] is None
    assert result['decision']['code']=='REVIEW_REQUIRED'


@pytest.mark.parametrize('drug,indication',[('Sitagliptin','type 2 diabetes'),('Metformin','infection'),('Metformin',''),('','type 2 diabetes')])
def test_indication_and_drug_must_match_document(drug,indication):
    result=assess_medication(patient(egfr=38),drug,indication)
    assert result['document_findings']==[]
    assert result['decision']['code']=='REVIEW_REQUIRED'
    assert result['status']!='SIMULATION'
    assert result['alternatives']==[]


@pytest.mark.parametrize('changes',[{'stable':False},{'verified':False},{'dialysis':None},{'collected_at':datetime.now(timezone.utc)-timedelta(hours=72)}])
def test_unready_data_suppress_source_band_matching(changes):
    result=assess_medication(patient(egfr=38,**changes),'Metformin','type 2 diabetes')
    assert result['document_findings']==[]
    assert result['decision']['code']=='REVIEW_REQUIRED'
    assert not result['decision']['actionable']


def test_api_assesses_selected_drug_and_preserves_document_provenance():
    c=client('physician')
    payload={'patient':patient(egfr=38).model_dump(mode='json'),'drug':'Metformin','indication':'type 2 diabetes'}
    result=c.post('/assess',json=payload).json()
    assert result['document_findings'][0]['matched_band']['source_category']=='ADJUST'
    payload['drug']='Gabapentin'
    assert c.post('/assess',json=payload).json()['document_findings']==[]
    doc=c.get('/knowledge/documents').json()[0]
    assert doc['sha256']=='eb8c164d43577dca0760f2be4994055b9d3e2e7d183098731539501898ed51c4'
    assert 'draft' in doc['filename'] and doc['status']=='PENDING_CLINICAL_VALIDATION'
