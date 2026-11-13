"""REV13: auditoria deterministica, sem executar solver nem alterar MILP.
Executar na raiz do repositorio REV05 com relatorios REV12 presentes.
"""
import argparse,csv,hashlib,json,math,re,sys
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]

def read_json(path):
    if not path.is_file(): raise FileNotFoundError(f'REQUIRED_REPORT_MISSING: {path}')
    return json.loads(path.read_text(encoding='utf-8'))

def fnum(v):
    try:return float(v)
    except (TypeError,ValueError):return None

def inspect_csv(path,expected_hash):
    if not path.is_file():raise FileNotFoundError(f'SERIES_MISSING: {path}')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_hash and digest!=expected_hash:raise RuntimeError('INPUT_SHA256_MISMATCH: refusing analysis')
    with path.open(encoding='utf-8-sig',newline='') as fh:
        rd=csv.DictReader(fh); cols=rd.fieldnames or []; rows=list(rd)
    return digest,cols,rows

def find_col(cols,candidates):
    names={re.sub(r'[^a-z0-9]','',c.lower()):c for c in cols}
    for cand in candidates:
        k=re.sub(r'[^a-z0-9]','',cand.lower())
        if k in names:return names[k]
    return None

def audit_source(root):
    p=root/'src/d28/dispatch/milp.py'
    if not p.exists():return {'status':'SOURCE_MISSING','path':str(p)}
    src=p.read_text(encoding='utf-8')
    checks={
      'binary_mode':r'm\.bess_mode\s*=\s*p\.Var\(m\.T,\s*domain\s*=\s*p\.Binary',
      'charge_mode':r'm\.bess_charge\[t\]\s*<=\s*pcs_power_kw\s*\*\s*m\.bess_mode\[t\]',
      'discharge_mode':r'm\.bess_discharge\[t\]\s*<=\s*pcs_power_kw\s*\*\s*\(1\s*-\s*m\.bess_mode\[t\]\)',
      'energy_balance':r'm\.bess_energy\[t\s*\+\s*1\]',
      'pv_curtailment':r'm\.pv\[t\]\s*\+\s*m\.pv_curt\[t\]',
      'initial_soc':r'm\.bess_energy\[0\]\s*==\s*initial_soc\s*\*\s*capacity_usable',
      'cyclic_terminal':r'm\.bess_energy\[n\]\s*==\s*m\.bess_energy\[0\]',
      'grid_cap':r'bounds\s*=\s*\(0,\s*pcc_cap_kw\)',
    }
    found={k:bool(re.search(pattern,src)) for k,pattern in checks.items()}
    return {'status':'STATIC_SOURCE_CHECK','path':str(p.relative_to(root)),
            'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
            'checks':found,'all_patterns_found':all(found.values()),
            'interpretation':'Syntax-only: does not prove numerical or mathematical correctness'}

def main():
    ap=argparse.ArgumentParser(description='REV13: intervalos criticos e formulacao binaria; sem solve')
    ap.add_argument('--scenario',default='E100')
    ap.add_argument('--window',type=int,default=8,help='intervalos antes/depois')
    args=ap.parse_args()
    if args.window<0 or args.window>96:raise ValueError('window must be between 0 and 96')
    paths={key:ROOT/'results'/f'rev12_relax_{args.scenario}_{mode}_{policy}.json'
           for key,mode,policy in [('lp_physical','lp','physical'),('lp_protect_pcc','lp','protect-pcc'),('milp_physical','milp','physical')]}
    reports={k:read_json(v) for k,v in paths.items()}
    for k,r in reports.items():
        if r.get('policy')!=('protect-pcc' if k=='lp_protect_pcc' else 'physical'):raise RuntimeError('POLICY_MISMATCH: '+k)
        if r.get('intervals')!=35040:raise RuntimeError('NOT_ANNUAL_REPORT: '+k)
    base=reports['lp_physical']; prov=base.get('provenance',{}).get('series',{})
    series=ROOT/Path(prov['path']);digest,cols,rows=inspect_csv(series,prov.get('sha256'))
    if len(rows)!=35040:raise RuntimeError(f'SERIES_LENGTH_MISMATCH: {len(rows)}')
    loadcol=find_col(cols,['load_kw','demand_kw','load','demanda_kw','p_load_kw'])
    pvcol=find_col(cols,['pv_pu','pv_factor','pv_cf','solar_pu','pv_per_unit'])
    timecol=find_col(cols,['timestamp','datetime','date_time','data_hora','time','date'])
    pcc=2500.0;pv_kw=float(base['design']['pv_kw']);bess=float(base['design']['bess_kwh']);pcs=float(base['design']['pcs_kw']);dt=float(base['dt_hours'])
    top=base.get('top_violations',{}).get('pcc',[])
    if not top:raise RuntimeError('LP_TOP_PCC_MISSING: REV12 report must include top_violations.pcc')
    indices=sorted(set(int(x['interval_index']) for x in top if float(x['value'])>1e-6))
    all_critical=[]; windows=[]
    for idx in indices:
        if not 0<=idx<len(rows):raise RuntimeError('INVALID_INTERVAL_INDEX')
        r=rows[idx];load=fnum(r.get(loadcol)) if loadcol else None;pvpu=fnum(r.get(pvcol)) if pvcol else None
        pvmax=pv_kw*pvpu if pvpu is not None else None
        net=load-pvmax if load is not None and pvmax is not None else None
        # lower bound for instantaneous discharge from grid+PV, NOT a full SOC feasibility certificate
        need=max(0,net-pcc) if net is not None else None
        viol=next(float(x['value']) for x in top if int(x['interval_index'])==idx)
        entry={'index_zero_based':idx,'row_one_based':idx+2,'timestamp_in_series':r.get(timecol) if timecol else None,
               'lp_pcc_slack_kw':viol,'lp_implied_grid_kw':pcc+viol,'load_kw':load,
               'pv_pu':pvpu,'pv_available_kw':pvmax,'net_load_without_bess_kw':net,
               'instantaneous_discharge_lower_bound_kw':need,
               'pcs_kw':pcs,'instantaneous_capacity_test':None if need is None else need<=pcs+1e-6}
        all_critical.append(entry)
        for j in range(max(0,idx-args.window),min(len(rows),idx+args.window+1)):
            row=rows[j];lv=fnum(row.get(loadcol)) if loadcol else None;pf=fnum(row.get(pvcol)) if pvcol else None
            windows.append({'critical_index':idx,'index_zero_based':j,'offset_intervals':j-idx,
                            'timestamp_in_series':row.get(timecol) if timecol else None,
                            'load_kw':lv,'pv_pu':pf,'pv_available_kw':pv_kw*pf if pf is not None else None,
                            'net_load_without_bess_kw':lv-pv_kw*pf if lv is not None and pf is not None else None})
    outdir=ROOT/'results';outdir.mkdir(exist_ok=True)
    with (outdir/f'rev13_windows_{args.scenario}.csv').open('w',newline='',encoding='utf-8-sig') as fh:
        w=csv.DictWriter(fh,fieldnames=list(windows[0]));w.writeheader();w.writerows(windows)
    milp=reports['milp_physical']; ub=fnum(milp.get('solver_best_feasible_objective'));lb=fnum(milp.get('solver_best_objective_bound'))
    gap=(ub-lb)/max(abs(ub),1e-12) if ub is not None and lb is not None else None
    source=audit_source(ROOT)
    conclusion={
      'scope':'REV13_DIAGNOSTIC_NO_SOLVER','scenario':args.scenario,'annual_intervals':len(rows),
      'series_sha256_verified':digest,'csv_columns':cols,
      'source_binary_audit':source,'lp_critical_intervals':all_critical,
      'lp_pcc_total_kwh':base['violations']['pcc']['sum_kwh_equivalent'],
      'lp_protect_pcc_soc_low':reports['lp_protect_pcc']['violations']['soc_low'],
      'lp_protect_pcc_soc_high':reports['lp_protect_pcc']['violations']['soc_high'],
      'milp_best_feasible_objective':ub,'milp_best_objective_bound':lb,
      'milp_relative_gap':gap,'milp_status':milp['status'],
      'warnings':[
        'LP physical optimum is a LOWER BOUND for the MILP diagnostic objective, not necessarily a structural PCC threshold.',
        'MILP incumbent is an UPPER BOUND on minimum diagnostic violation, not a required PCC rating.',
        'Relaxing binary mode allows simultaneous charge/discharge in LP. No dispatch values saved in REV12; cannot measure simultaneity ex post.',
        'SOC penalties are sums of per-state excursions in kWh, not additional battery capacity or energy throughput.',
        'Static source check is not a proof of equivalence or feasibility. No solver was run.',
        'Window CSV provides load/PV context only, not reconstructed SOC or optimized dispatch.',
      ],'next_steps':[
        'Save full LP dispatch (charge, discharge, bess_mode, SOC, grid) in a separate bounded or annual LP solve to quantify simultaneity.',
        'Use LP solution as warm start only if supported; benchmark short windows before another annual MILP.',
        'Test explicit feasibility certificates with fixed PCC and all physical constraints before changing design.',
      ]}
    target=outdir/f'rev13_auditoria_{args.scenario}.json';target.write_text(json.dumps(conclusion,ensure_ascii=False,indent=2),encoding='utf-8')
    print('REV13 STATIC AUDIT: NO SOLVER RUN')
    print('SHA256 verified:',digest)
    print('LP critical intervals:',indices)
    for e in all_critical:print(' index',e['index_zero_based'],'load',e['load_kw'],'PV',e['pv_available_kw'],'PCC slack',e['lp_pcc_slack_kw'])
    print('MILP relative gap:',gap,'source checks:',source.get('checks'))
    print('REPORT:',target)
    print('WINDOWS:',outdir/f'rev13_windows_{args.scenario}.csv')

if __name__=='__main__':main()
