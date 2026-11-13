#!/usr/bin/env python3
"""REV16.1.3e: registra PKM sintetico E100 e audita F1 sem executar MILP.
Uso: python d28_rev16_1_3e_g2.py --inspect | --apply | --audit
"""
import argparse
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PKM = 137675700
FILES = {
    'evidence': ROOT / 'config/annual_f1_f2_evidence.json',
    'economics': ROOT / 'config/economics/r0_f1_exploratory_2026.json',
    'objectives': ROOT / 'config/experiments/r0_objective_inputs.json',
    'g1': ROOT / 'results/D28_REV16_1_3c_G1_CONSOLIDADO.json',
}
REPORT = ROOT / 'results/D28_REV16_1_3e_G2_AUDITORIA.json'

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def close(a, b, rel=1e-9, abs_=1e-5):
    return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=abs_)

def inspect():
    for k,p in FILES.items():
        print(f'{k}: {p.relative_to(ROOT)} | exists={p.is_file()}')
        if p.is_file() and k != 'g1':
            d=read(p)
            if k=='evidence': print('  annual_pkm_approved:',d.get('annual_pkm_approved'))
            if k=='economics': print('  annual_pkm:',d.get('annual_pkm'),'status:',d.get('annual_pkm_status'))
            if k=='objectives': print('  economic.annual_pkm:',d.get('economic',{}).get('annual_pkm'))

def apply():
    missing=[str(p) for p in FILES.values() if not p.is_file()]
    if missing: raise RuntimeError('Arquivos ausentes: '+', '.join(missing))
    ev,ec,ob=(read(FILES[k]) for k in ('evidence','economics','objectives'))
    if not isinstance(ob.get('economic'),dict): raise RuntimeError('Objeto economic ausente')
    for value in (ec.get('annual_pkm'),ob['economic'].get('annual_pkm')):
        if value is not None and not close(value,PKM,rel=0,abs_=0):
            raise RuntimeError('PKM preexistente divergente; nenhuma alteracao feita')
    # Preserva o indice historico REV08 e todos os bloqueios nao relacionados ao PKM.
    ev['annual_pkm_approved']=True
    ev['annual_pkm_approval_scope']='E100_SYNTHETIC_METHODOLOGICAL_REFERENCE_ONLY'
    ev['annual_pkm_approval_basis']='RESEARCHER_EXPLICIT_DECISION'
    ev['annual_pkm_approved_value']=PKM
    ec['annual_pkm']=PKM
    ec['annual_pkm_status']='APPROVED'
    ec['annual_pkm_approval_scope']='E100_SYNTHETIC_METHODOLOGICAL_REFERENCE_ONLY'
    ob['economic']['annual_pkm']=PKM
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=ROOT/'results'/'backups'/('REV16_1_3e_'+stamp)
    backup.mkdir(parents=True,exist_ok=False)
    original_hashes={}
    for key in ('evidence','economics','objectives'):
        p=FILES[key]; original_hashes[key]=sha(p)
        shutil.copy2(p,backup/p.name)
    updates={'evidence':ev,'economics':ec,'objectives':ob}
    for key,data in updates.items():
        p=FILES[key]
        tmp=p.with_name(p.name+'.rev16_1_3e.tmp')
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        tmp.replace(p)
    manifest={'revision':'REV16.1.3e','backup':str(backup),'original_sha256':original_hashes,
              'pkm':PKM,'scope':'E100_SYNTHETIC_METHODOLOGICAL_REFERENCE_ONLY',
              'note':'Existing evidence references/hash manifests are historical; do not rewrite them automatically.'}
    (backup/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Atualizacao concluida. Backup:',backup)
    print('Atencao: hashes historicos de referencias nao foram recalculados.')

def audit():
    missing=[str(p) for p in FILES.values() if not p.is_file()]
    if missing: raise RuntimeError('Arquivos ausentes: '+', '.join(missing))
    ev,ec,ob,g1=(read(FILES[k]) for k in ('evidence','economics','objectives','g1'))
    pkm_ok=(ev.get('annual_pkm_approved') is True
            and ev.get('annual_pkm_approval_scope')=='E100_SYNTHETIC_METHODOLOGICAL_REFERENCE_ONLY'
            and ec.get('annual_pkm_status')=='APPROVED'
            and ec.get('annual_pkm_approval_scope')=='E100_SYNTHETIC_METHODOLOGICAL_REFERENCE_ONLY'
            and ec.get('annual_pkm')==PKM
            and isinstance(ob.get('economic'),dict)
            and ob['economic'].get('annual_pkm')==PKM)
    h=ec['horizon_years']; rate=ec['discount_rate_real_year']
    annuity=sum((1+rate)**(-year) for year in range(1,h+1))
    pv_pkm=PKM*annuity
    rows=g1.get('rows',[])
    expected=[2500,2450,2400,2300]
    structure_ok=(g1.get('status')=='PASS_R0_MILP_BILL_VP_RECONCILED'
                  and len(rows)==4 and [r.get('epsilon_kw') for r in rows]==expected)
    result=[]
    for r in rows:
        cost=r['pv_total_cost_brl']; milp=r['milp_objective_brl']
        bill=r['annual_energy_total_brl']
        decomposed=(r['initial_capex_brl']+
                    (r['annual_fixed_opex_brl']+bill)*annuity+
                    r['replacement_present_value_brl'])
        checks={
            'g1_row_pass':r.get('gate')=='PASS' and r.get('status')=='PASS',
            'all_g1_checks':all(r.get('checks',{}).values()) and bool(r.get('checks')),
            'milp_bill':close(milp,bill),
            'bill_components':close(bill,r['annual_energy_charge_brl']+r['annual_demand_charge_brl']),
            'vp_decomposition':close(cost,decomposed),
            'annuity_matches_g1':close(annuity,r['annuity_factor']),
            'epsilon_feasible':r['f2_kw']<=r['epsilon_kw']+1e-5,
        }
        result.append({'epsilon_kw':r['epsilon_kw'],'f2_kw':r['f2_kw'],
                       'milp_cost_brl':milp,'pv_total_cost_brl':cost,
                       'pv_pkm':pv_pkm,'f1_brl_per_pkm':cost/pv_pkm,
                       'checks':checks,'pass':all(checks.values())})
    monotonic=[]
    sorted_rows=sorted(result,key=lambda r:r['epsilon_kw'])
    for restrictive,relaxed in zip(sorted_rows,sorted_rows[1:]):
        excess=relaxed['milp_cost_brl']-restrictive['milp_cost_brl']
        monotonic.append({'epsilon_restrictive_kw':restrictive['epsilon_kw'],
                          'epsilon_relaxed_kw':relaxed['epsilon_kw'],
                          'unexpected_cost_increase_brl':max(0,excess),
                          'requires_solver_optimality_review':excess>1e-3})
    g2_arithmetic_pass=pkm_ok and structure_ok and len(result)==4 and all(r['pass'] for r in result)
    report={'revision':'REV16.1.3e','classification':'SYNTHETIC_REFERENCE_EXPLORATORY_ECONOMICS',
            'pkm_annual':PKM,'pkm_approved_for_E100':pkm_ok,
            'g1_structure_ok':structure_ok,'discount_rate':rate,'horizon_years':h,
            'annuity_factor':annuity,'pv_pkm':pv_pkm,'rows':result,
            'monotonicity':monotonic,
            'g2_arithmetic_status':'PASS' if g2_arithmetic_pass else 'BLOCKED',
            'optimization_certification':'PENDING_MIP_GAP_BOUNDS_AND_MONOTONICITY_REVIEW',
            'nsga2_authorization':False,
            'scope_notes':['No MILP or NSGA-II executed',
                           'PKM homologation is synthetic, not observed operational data',
                           'Tariff, temporal series, and other historical evidence blocks unchanged',
                           'G1 checks verify accounting identities, not global optimality',
                           'Inspect existing hashes in evidence index after configuration edits']}
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PKM_CONFIG:', 'PASS' if pkm_ok else 'BLOCKED')
    print('G1_STRUCTURE:', 'PASS' if structure_ok else 'BLOCKED')
    print(f'VP_PKM: {pv_pkm:.4f}')
    for r in result:
        print(f"epsilon={r['epsilon_kw']:.0f} | F2={r['f2_kw']:.4f} kW | F1={r['f1_brl_per_pkm']:.9f} R$/PKM | checks={'PASS' if r['pass'] else 'FAIL'}")
    for m in monotonic:
        if m['requires_solver_optimality_review']:
            print(f"MONOTONICITY_REVIEW: {m['epsilon_restrictive_kw']:.0f}->{m['epsilon_relaxed_kw']:.0f} | excess={m['unexpected_cost_increase_brl']:.4f} BRL")
    print('G2_ARITHMETIC:',report['g2_arithmetic_status'])
    print('NSGA2_AUTHORIZED: False')
    print('REPORT:',REPORT)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--inspect',action='store_true')
    group.add_argument('--apply',action='store_true')
    group.add_argument('--audit',action='store_true')
    args=parser.parse_args()
    if args.inspect: inspect()
    elif args.apply: apply()
    else: audit()
