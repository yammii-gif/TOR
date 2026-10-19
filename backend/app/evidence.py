"""Retrieval never creates or activates rules. Raw provenance is retained."""
from datetime import datetime, timezone
import httpx
class LicensedProvider:
    def retrieve(self,drug):return {'status':'LICENSE_REQUIRED','drug':drug,'sources':['Lexidrug','Micromedex']}
class DailyMedProvider:
    def retrieve(self,drug):
        url='https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json'
        with httpx.Client(timeout=30,follow_redirects=True) as c:
            r=c.get(url,params={'drug_name':drug});r.raise_for_status()
        return {'status':'DRAFT','source':'DailyMed','url':str(r.url),'access_date':datetime.now(timezone.utc).isoformat(),'raw':r.json(),'reviewer':None,'warning':'Search results only; label and version require independent review'}
def conflict(sources):return 'SOURCE_CONFLICT' if len(set(sources))>1 else 'PENDING_REVIEW'

from pydantic import BaseModel, Field
class Provenance(BaseModel):
    source_name:str
    url:str
    source_version:str
    accessed_at:str
    exact_excerpt:str
    reviewer:str|None=None
class DrugKnowledge(BaseModel):
    generic_name:str
    brand_names:list[str]=Field(default_factory=list)
    indications:list[str]=Field(default_factory=list)
    forms_strengths:list[str]=Field(default_factory=list)
    usual_dosing:str|None=None
    renal_measure:str|None=None
    renal_thresholds:list[dict]=Field(default_factory=list)
    adjusted_dose:str|None=None
    interval:str|None=None
    contraindications:list[str]=Field(default_factory=list)
    precautions:list[str]=Field(default_factory=list)
    administration:list[str]=Field(default_factory=list)
    adverse_effects:list[str]=Field(default_factory=list)
    monitoring:list[str]=Field(default_factory=list)
    alternatives:list[dict]=Field(default_factory=list)
    rationale:str|None=None
    provenance:list[Provenance]=Field(default_factory=list)
    approval_status:str='DRAFT'
