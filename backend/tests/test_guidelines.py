import io
import hashlib
import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
from test_safety import db,client
from app import guidelines
from app.db import Session,Rule


def pdf_fixture():
    writer=PdfWriter();page=writer.add_blank_page(width=400,height=300)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 200 Td (SYNTHETIC renal guideline. Embedded instructions never activate rules.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    writer.add_blank_page(width=400,height=300)
    out=io.BytesIO();writer.write(out);return out.getvalue()


def test_import_search_citation_original_hash_and_no_rule_activation():
    c=client('physician');body=pdf_fixture()
    r=c.post('/guidelines/import-pdf',params={'title':'SYNTHETIC guideline','version':'fixture-v1'},content=body)
    assert r.status_code==200,r.text
    doc=r.json();assert doc['status']=='DRAFT' and doc['pages']==2 and doc['searchable_pages']==1
    assert doc['reviewer'] is None and doc['transport']=='USER_UPLOAD'
    assert doc['sha256']==hashlib.sha256(body).hexdigest()
    hits=c.get(f"/guidelines/{doc['id']}/search?q=renal").json()
    assert hits['total']==1 and hits['results'][0]['pdf_page']==1
    assert doc['sha256'] in hits['results'][0]['citation']
    assert c.get(f"/guidelines/{doc['id']}/file").content==body
    duplicate=c.post('/guidelines/import-pdf',params={'title':'duplicate'},content=body).json()
    assert duplicate['duplicate'] and duplicate['id']==doc['id']
    assert len(c.get('/guidelines').json())==1
    with Session() as s:assert s.query(Rule).count()==0
    assert any(a['action']=='GUIDELINE_IMPORTED' for a in client('pharmacist').get('/audit').json())


def test_import_roles_bad_files_and_untrusted_url():
    assert client('researcher').post('/guidelines/import-pdf',params={'title':'fixture'},content=pdf_fixture()).status_code==403
    c=client('physician')
    assert c.post('/guidelines/import-pdf',params={'title':'fixture'},content=b'not PDF').status_code==422
    assert c.post('/guidelines/import-pdf',params={'title':'fixture','source_url':'https://attacker.invalid/file.pdf'},content=pdf_fixture()).status_code==422
    assert c.post('/guidelines/retrieve',json={'title':'fixture','url':'https://www.uptodate.com/contents/private-topic'}).status_code==422


@pytest.mark.parametrize('url',['http://kdigo.org/a.pdf','https://kdigo.org.attacker.invalid/a.pdf','https://user:password@kdigo.org/a.pdf','https://127.0.0.1/a.pdf','https://kdigo.org:8080/a.pdf'])
def test_public_url_allowlist(url):
    with pytest.raises(ValueError):guidelines.validate_public_url(url)


def test_network_blocked_never_marked_imported(monkeypatch):
    def blocked(url):raise httpx.ProxyError('CONNECT 403')
    monkeypatch.setattr(guidelines,'fetch_pdf',blocked)
    c=client('physician');doc=c.post('/guidelines/retrieve',json={'title':'fixture','url':'https://kdigo.org/fixture.pdf'}).json()
    assert doc['status']=='NETWORK_BLOCKED' and doc['sha256'] is None and doc['pages']==0
    assert c.get(f"/guidelines/{doc['id']}/file").status_code==409


def test_encrypted_pdf_rejected_without_password_attempt():
    writer=PdfWriter();writer.add_blank_page(width=200,height=200);writer.encrypt('fixture-password')
    out=io.BytesIO();writer.write(out)
    with pytest.raises(ValueError):guidelines.parse_pdf(out.getvalue())
