"""Validate manually transcribed periodic court reports without inventing missing fields."""
import re
from pathlib import Path
import pandas as pd

FIELDS = ['court_level','state','district','court_label','month','category','opening','instituted','disposed','pending','source_page']


def validate_periodic(path, provenance, control):
    """Keep stocks at their reported date and derive clearance only from reported flows."""
    header = list(pd.read_csv(path,nrows=0).columns)
    if any(re.search(r'name|phone|aadhaar|address|party|accused',c,re.I) for c in header):
        raise ValueError('Personal-data columns refused in periodic report')
    if header != FIELDS:
        raise ValueError('Periodic report schema mismatch')
    data = pd.read_csv(path,keep_default_na=False,dtype=str)
    if provenance['source_url'] != control['source_url']:
        raise ValueError('Periodic report URL does not match reviewed controls')
    if len(data) != control['rows'] or sorted(data.month.unique()) != control['months']:
        raise ValueError('Periodic report row or month coverage mismatch')
    if data.duplicated(['month','category']).any():
        raise ValueError('Duplicate periodic month/category')
    for row in data.to_dict('records'):
        for key in ['court_level','state','district','court_label']:
            if row[key] != control[key]:
                raise ValueError('Periodic reporting identity mismatch')
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',row['month']):
            raise ValueError('Invalid periodic month')
        if not provenance['coverage_start'] <= row['month'] <= provenance['coverage_end']:
            raise ValueError('Periodic month outside provenance coverage')
        for key in ['opening','instituted','disposed','pending','source_page']:
            if key=='opening' and row[key]=='':continue
            if not re.fullmatch(r'\d+',row[key]):raise ValueError('Periodic counts must be nonnegative integers')
        if int(row['source_page']) != control['source_page']:
            raise ValueError('Periodic report page differs from reviewed table')
        if row['opening'] and int(row['opening'])+int(row['instituted'])-int(row['disposed']) != int(row['pending']):
            raise ValueError('Periodic opening + institutions - disposals does not reconcile')
    for month, group in data.groupby('month'):
        if set(group.category) != {'Civil','Criminal','Total'}:
            raise ValueError('Periodic report requires separate Civil, Criminal and Total rows')
        indexed=group.set_index('category')
        for key in ['opening','instituted','disposed','pending']:
            values=indexed[key]
            if (values=='').all():continue
            if (values=='').any() or int(values['Civil'])+int(values['Criminal']) != int(values['Total']):
                raise ValueError('Periodic Civil + Criminal totals do not reconcile')
    totals=data[data.category=='Total'].sort_values('month')
    observed={key:int(totals[key].astype(int).sum()) for key in ['instituted','disposed']}
    observed['last_pending']=int(totals.iloc[-1]['pending'])
    if observed != control['control_totals']:
        raise ValueError('Periodic published controls do not reconcile')
    result=[]
    for row in data.to_dict('records'):
        for key in ['opening','instituted','disposed','pending','source_page']:
            row[key]=int(row[key]) if row[key] != '' else None
        row['source']=provenance
        row['clearance_rate']={'value':row['disposed']/row['instituted'] if row['instituted'] else None,
                               'method':'Reported monthly disposals divided by reported institutions; unavailable when institutions are zero.'}
        row['pendency_rate']={'value':row['pending']/row['opening'] if row['opening'] else None,
                              'method':'Reported month-end pending divided by reported opening pending; no opening is back-calculated.'}
        row['pending_method']='Reported month-end stock; never summed across months or with Total plus category components.'
        row['adjournment_rate']={'value':None,'method':'Hearings listed and adjourned are not reported in these selected tables.'}
        result.append(row)
    return result


def load_periodic(raw_root, source_map, controls):
    """Load only registered, reviewed report files, with per-report definitions and dates."""
    records=[]
    for filename, control in controls.items():
        if filename not in source_map or not (Path(raw_root)/filename).is_file():
            raise ValueError('Periodic report missing its raw file or sources.csv entry: '+filename)
        records.extend(validate_periodic(Path(raw_root)/filename,source_map[filename]._asdict(),control))
    return {'records':records,'reports':list(controls.values()),
            'coverage_note':'Partial district coverage: one district in Assam. Supreme Court monthly data Jan–Aug 2025. These reports are separate from the March 2026 national snapshot.',
            'limitations':['Only the listed reports and periods have been verified; this is not nationwide district coverage.',
                           'Do not add Total rows to Civil/Criminal components or add stocks across months.',
                           'Hearings and adjournments are not supplied. No individual case records are collected.',
                           'Supreme Court annual report reserves reproduction rights; no commercial data clearance is claimed.']}
