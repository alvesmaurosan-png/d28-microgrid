"""Auditoria fail-closed da liberação científica anual D28; não executa MILP.
Uso: python scripts/07_auditar_liberacao_anual.py
"""
import hashlib
import json
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ('R0','R1','R2','R3')

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def audit(root=ROOT):
    root=Path(root)
    contract_file=root/'contrato_anual.json'
    base_files=list(root.glob('data/raw/**/Base_Mestre_D28_PC_REV07_REV02.xlsx'))
    findings=[]
    def check(key, ok, detail): findings.append({'id':key,'pass':bool(ok),'detail':str(detail)})
    contract={}
    if contract_file.is_file():
        try: contract=json.loads(contract_file.read_text(encoding='utf-8-sig'))
        except (ValueError,UnicodeError) as exc: check('CONTRACT_PARSE',False,str(exc))
    check('CONTRACT_PRESENT',contract_file.is_file(),str(contract_file))
    check('CONTRACT_APPROVED',contract.get('status')=='APPROVED',contract.get('status','MISSING'))
    check('MAPPING_EVIDENCE_APPROVED',contract.get('mapping_evidence_status')=='APPROVED',contract.get('mapping_evidence_status','MISSING'))
    year=contract.get('year')
    try:
        year=int(year); start=date(year,1,1); end=date(year+1,1,1)
        days={(start+timedelta(days=i)).isoformat() for i in range((end-start).days)}
        mapping=contract.get('source_day_for_calendar_day')
        mapping_ok=isinstance(mapping,dict) and set(mapping)==days and all(isinstance(v,str) and v.strip() for v in mapping.values())
        expected_intervals=len(days)*96
    except (TypeError,ValueError,OverflowError):
        mapping_ok=False; expected_intervals=None
    check('COMPLETE_CALENDAR_MAPPING',mapping_ok,f'expected_intervals={expected_intervals}')
    check('MAPPING_RATIONALE',bool(str(contract.get('calendar_mapping_rationale') or '').strip()),'explicit rationale required')
    check('BASE_MASTER_PRESENT',bool(base_files),'; '.join(map(str,base_files)))
    check('ECONOMIC_DISPATCH_PRESENT',(root/'src/d28/optimization/economic_dispatch_f1f2.py').is_file(),'R0-R3 dispatch adapter')
    check('ANNUAL_ACCOUNTING_PRESENT',(root/'src/d28/optimization/biobjective_f1_f2.py').is_file(),'annual_f1_f2')
    check('ANNUAL_CONNECTOR_PRESENT',(root/'src/d28/optimization/annual_f1_f2_connector_rev06.py').is_file(),'REV06 connector')
    manifest_path=root/'config/annual_f1_f2_evidence.json'
    try: evidence=json.loads(manifest_path.read_text(encoding='utf-8-sig')) if manifest_path.is_file() else {}
    except (ValueError,UnicodeError): evidence={}
    check('EVIDENCE_MANIFEST_PRESENT',manifest_path.is_file(),str(manifest_path))
    for key in ('temporal_series_approved','energy_prices_approved','annual_pkm_approved','economic_parameters_approved','annual_cost_reconciliation_approved','r2_gas_loss_accounting_approved','r3_cgob_accounting_approved','auxiliary_no_double_count_approved'):
        check(key.upper(),evidence.get(key) is True,'explicit true with independent supporting evidence required')
    references=evidence.get('references')
    check('EVIDENCE_REFERENCES',isinstance(references,dict) and all(bool(references.get(k)) for k in ('temporal','tariffs','pkm','economics','r2','r3','auxiliaries')),'references must identify source files/records')
    paths=[contract_file,*base_files,manifest_path]
    report={'protocol':'D28_REV07_ANNUAL_F1_F2_RELEASE_AUDIT','scientific_release':all(f['pass'] for f in findings),
            'milp_annual_executed':False,'nsga2_executed':False,'f3_excluded':True,
            'expected_15min_intervals':expected_intervals,'routes':list(ROUTES),
            'files_sha256':{str(p.relative_to(root)):sha256(p) for p in paths if p.is_file()},'checks':findings}
    return report

if __name__=='__main__':
    report=audit()
    out=ROOT/'results/rev07_gate_anual_f1_f2.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('ANNUAL_RELEASE', 'READY_FOR_FURTHER_VALIDATION' if report['scientific_release'] else 'BLOCKED')
    print('Checks:',sum(x['pass'] for x in report['checks']),'/',len(report['checks']))
    print('Report:',out)
