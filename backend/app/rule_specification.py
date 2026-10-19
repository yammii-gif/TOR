"""Unfilled structured renal rule template; no clinical claims or doses."""

def renal_rule_template(generic_name):
    return {
        'schema_version': 1, 'generic_name': generic_name,
        'brand_names': [], 'indications': [], 'forms_and_strengths': [],
        'renal_measure': None, 'renal_unit': None,
        'applicable_conditions': [], 'exclusions': [],
        'usual_dose': None, 'thresholds': [],
        'adjusted_dose': None, 'route': None, 'interval': None, 'duration': None,
        'contraindications': [], 'precautions': [], 'interactions': [],
        'administration': None, 'adverse_effects': [], 'monitoring': [],
        'alternatives': [], 'clinical_rationale': None,
        'sources': [],
        'evidence_level': None, 'evidence_grading_system': None,
        'checked_at': None, 'reviewer': None,
        'institutional_approval': None,
        'validation_status': 'PENDING_CLINICAL_VALIDATION',
        'note': 'Empty fields are unverified, not evidence of absence. No actionable dosing.',
    }
