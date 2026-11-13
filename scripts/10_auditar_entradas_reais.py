"""Auditoria REV10 dos insumos reais. Nunca promove homologação automaticamente."""
from pathlib import Path
import json,hashlib,csv,calendar,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    manifest=json.loads((ROOT/'config/annual_f1_f2_evidence.json').read_text(encoding='utf-8-sig'))
    contract=json.loads((ROOT/'contrato_anual.json').read_text(encoding='utf-8-sig'))
    evidence=[]
    for group,refs in manifest['references'].items():
        for r in refs:
            p=ROOT/r['path'];actual=sha(p) if p.is_file() else None
            evidence.append({'group':group,'path':r['path'],'expected_sha256':r['sha256'],'actual_sha256':actual,'verified':actual==r['sha256']})
    configpath=ROOT/'config/economics/r0_f1_exploratory_2026.json'
    econ=json.loads(configpath.read_text(encoding='utf-8-sig'))
    source=json.loads((ROOT/'data/processed/annual_charging/manifesto_anual.json').read_text(encoding='utf-8-sig'))
    milp=json.loads((ROOT/'data/processed/milp_inputs/R0_inputs_manifest.json').read_text(encoding='utf-8-sig'))
    rows=[]
    for scenario in milp['scenarios']:
        name=scenario['scenario'];path=ROOT/f'data/processed/milp_inputs/R0_inputs_{name}_15min.csv'
        count=0;energy=0.;peak=0.;months=set();bad=0
        if path.exists():
            with path.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f)
                for row in reader:
                    count+=1
                    try:
                        v=float(row['load_charging_ac_kw']);dt=float(row['dt_hours']);energy+=v*dt;peak=max(peak,v)
                        if dt!=.25 or v<0:bad+=1
                        months.add(row['interval_start_local'][:7])
                    except (KeyError,ValueError):bad+=1
        rows.append({'scenario':name,'file':str(path.relative_to(ROOT)),'count':count,'energy_kwh':round(energy,4),'manifest_energy_kwh':scenario['charging_energy_ac_kwh'],'energy_reconciled':abs(energy-scenario['charging_energy_ac_kwh'])<=1.,'peak_kw':round(peak,4),'pcc_limit_kw':econ['pcc_import_limit_kw'],'load_peak_exceeds_pcc':peak>econ['pcc_import_limit_kw'],'bad_rows':bad,'months_count':len(months),'valid_length':count==35040})
    approval={k:v for k,v in manifest.items() if k.endswith('_approved')}
    findings=[]
    if any(not r['verified'] for r in evidence):findings.append('EVIDENCE_HASH_MISMATCH_OR_MISSING')
    if any(not r['valid_length'] or not r['energy_reconciled'] or r['bad_rows'] for r in rows):findings.append('ANNUAL_SERIES_INTEGRITY')
    if any(r['load_peak_exceeds_pcc'] for r in rows):findings.append('CHARGING_PEAK_EXCEEDS_PCC_CAPACITY: feasibility requires validated flexibility/storage/CHP and dispatch; not proof of infeasibility')
    if contract.get('status')!='APPROVED':findings.append('CONTRACT_NOT_APPROVED')
    if not isinstance(contract.get('source_day_for_calendar_day'),dict) or len(contract['source_day_for_calendar_day'])!=365:findings.append('DAY_MAPPING_MISSING_OR_INCOMPLETE')
    if econ.get('status')!='HOMOLOGATED':findings.append('ECONOMICS_EXPLORATORY')
    if econ.get('annual_pkm') is None:findings.append('ANNUAL_PKM_UNSET')
    if not all(approval.values()):findings.append('EVIDENCE_APPROVALS_PENDING')
    report={'protocol':'D28_REV10_REAL_INPUT_AUDIT','scientific_release':not findings,'annual_milp_executed':False,'f1_f2_computed':False,'contract_status':contract.get('status'),'contract_model':contract.get('model'),'economics_status':econ.get('status'),'economics_config_path':str(configpath.relative_to(ROOT)),'economics_parameters':{k:v for k,v in econ.items() if k not in ('sources',)},'evidence_checks':evidence,'series_checks':rows,'approval_flags':approval,'blocking_findings':findings,'note':'No approval inferred from presence, hashes, or methodological H1-H7 agreement. No annual MILP run without approved contract and actual model inputs.'}
    dest=ROOT/'results/rev10_real_inputs_audit.json';dest.parent.mkdir(exist_ok=True,parents=True);dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('REV10 SCIENTIFIC RELEASE:', 'APPROVED' if report['scientific_release'] else 'BLOCKED')
    print('EVIDENCE HASHES:',sum(x['verified'] for x in evidence),'/',len(evidence))
    print('ANNUAL SERIES:',sum(x['valid_length'] and x['energy_reconciled'] and not x['bad_rows'] for x in rows),'/',len(rows))
    print('PENDING:',', '.join(findings))
    print('REPORT:',dest)
    return 0 if report['scientific_release'] else 2
if __name__=='__main__':sys.exit(main())
