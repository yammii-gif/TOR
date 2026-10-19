from datetime import datetime,timezone
import pytest
from test_safety import db,client
from app.db import Session,FormularyItem
from app.formulary import parse_rows,parse_xls,import_items

HEADERS=['รหัส','ชื่อยา','ชื่อสามัญ','ความแรง','Dosage Form','ยาหมด','อยู่ในบัญชี','ราคาทุน']
ROWS=[['SYN-DRUG-1','Synthetic Drug A 10 mg','SYNTHETIC A','10 mg','Tablet','','',999],
      ['SYN-DRUG-2','Synthetic Drug A Eye','SYNTHETIC A','1%','Eye drops','','',500]]

def fixture_items():return parse_rows(HEADERS,ROWS,'a'*64)


def test_import_preserves_products_and_unknown_flags_without_prices():
    items=fixture_items()
    assert len(items)==2 and items[0]['source_row']==2
    assert 'ราคาทุน' not in items[0] and 'price' not in items[0]
    with Session.begin() as s:import_items(s,items)
    data=client('physician').get('/formulary').json()
    assert data['total']==2
    assert all(item['stock_status']=='UNKNOWN' for item in data['items'])
    assert {item['dosage_form'] for item in data['items']}=={'Tablet','Eye drops'}
    assert client('physician').get('/formulary?q=Eye').json()['matched']==1
    # Wildcards are escaped, not used to expand selection.
    assert client('physician').get('/formulary?q=%25').json()['matched']==0


def test_reimport_idempotent_and_new_export_invalidates_past_stock_check():
    with Session.begin() as s:import_items(s,fixture_items())
    c=client('pharmacist');assert c.post('/formulary/SYN-DRUG-1/stock',json={'status':'IN_STOCK'}).status_code==200
    with Session.begin() as s:import_items(s,fixture_items())
    assert c.get('/formulary?q=SYN-DRUG-1').json()['items'][0]['stock_status']=='IN_STOCK'
    changed=[item|{'source_hash':'b'*64} for item in fixture_items()]
    with Session.begin() as s:import_items(s,changed[:1])
    result=c.get('/formulary').json()
    assert result['total']==1 and result['items'][0]['stock_status']=='UNKNOWN'
    with Session() as s:assert s.query(FormularyItem).filter(FormularyItem.code.in_(['SYN-DRUG-1','SYN-DRUG-2'])).count()==2


def test_import_and_stock_roles_audit_and_atomic_rejection(monkeypatch):
    from app import formulary
    monkeypatch.setattr(formulary,'parse_xls',lambda _:fixture_items())
    physician=client('physician');pharmacist=client('pharmacist')
    assert physician.post('/formulary/import-xls',content=b'synthetic fixture').status_code==403
    assert pharmacist.post('/formulary/import-xls',content=b'synthetic fixture').json()['imported']==2
    assert physician.post('/formulary/SYN-DRUG-1/stock',json={'status':'IN_STOCK'}).status_code==403
    assert pharmacist.post('/formulary/SYN-DRUG-1/stock',json={'status':'OUT_OF_STOCK'}).json()['stock_checked_at']
    assert client('researcher').get('/formulary').status_code==403
    assert any(row['action']=='FORMULARY_IMPORTED' for row in pharmacist.get('/audit').json())
    def invalid(_):raise ValueError('workbook failure')
    monkeypatch.setattr(formulary,'parse_xls',invalid)
    assert pharmacist.post('/formulary/import-xls',content=b'bad').status_code==422
    assert pharmacist.get('/formulary').json()['total']==2


def test_bad_rows_and_non_xls_rejected():
    with pytest.raises(ValueError):parse_rows(['ชื่อยา'],[['bad']],'a'*64)
    with pytest.raises(ValueError):parse_rows(HEADERS,ROWS+[ROWS[0]],'a'*64)
    with pytest.raises(ValueError):parse_rows(HEADERS,[['','','','','','','','']],'a'*64)
    with pytest.raises(ValueError):parse_xls(b'<html>Not an XLS</html>')


def test_default_hospital_catalog_is_primary_and_not_synthetic_inventory():
    c=client('physician');inventory=c.get('/inventory').json()
    assert len(inventory)==827
    assert all(item['label']=='HOSPITAL FORMULARY' and item['stock_status']=='UNKNOWN' for item in inventory)
    assert len({item['code'] for item in inventory})==827
    assert not any(item['name']=='Sitagliptin' for item in inventory)
    assert any(item['code']=='1000997' and item['strength']=='500 MG' for item in inventory)
    assert c.post('/prescriptions',json={'drug':'Metformin','proposal':'manual fixture','decision':'MODIFY'}).status_code==422


def test_seed_restores_exact_product_links_without_duplicate_drug_records():
    from app.db import Drug,seed
    with Session.begin() as s:
        drug=s.query(Drug).filter_by(formulary_code='1000997').one()
        product_id=drug.id;drug.formulary_code=None
    seed()
    with Session() as s:
        assert s.query(Drug).filter_by(formulary_code='1000997').one().id==product_id
        assert s.query(Drug).filter(Drug.formulary_code.isnot(None)).count()==827
