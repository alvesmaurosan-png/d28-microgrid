"""REV16.1.4: executor exploratorio R0/E100 com gates economicos.

Executar na raiz D28_PC_REV08_REV02. Nao altera arquivos existentes.
O metodo e varredura epsilon de desenhos explicitamente informados, NAO NSGA-II.
Nenhum ponto e aceito sem solucao otima, conciliacao e F1 anual.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, sys
from datetime import datetime, timedelta
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(cond, msg):
    if not cond:
        raise ValueError(msg)


def load_inputs(path, year):
    """CSV: interval_start_local,load_charging_ac_kw,pv_kw_per_kwp,dt_hours."""
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    require(len(rows) == 35040, 'E100_REQUIRES_35040_ROWS')
    start = datetime(year, 1, 1)
    loads, solar, months = [], [], []
    for i, r in enumerate(rows):
        ts = datetime.fromisoformat(r['interval_start_local'])
        require(ts.tzinfo is None, 'LOCAL_TIMESTAMP_MUST_BE_NAIVE')
        require(ts == start + timedelta(minutes=15*i), f'TIMESTAMP_MISMATCH_AT_{i}')
        require(abs(float(r['dt_hours'])-0.25) < 1e-10, f'DT_MISMATCH_AT_{i}')
        l, s = float(r['load_charging_ac_kw']), float(r['pv_kw_per_kwp'])
        require(all(math.isfinite(x) and x >= 0 for x in (l,s)), f'INVALID_DATA_AT_{i}')
        if 'scenario' in r:
            require(r['scenario'].strip() == 'E100', f'WRONG_SCENARIO_AT_{i}')
        loads.append(l); solar.append(s); months.append(ts.year*100+ts.month)
    require(len(set(months)) == 12, 'MONTH_COUNT_INVALID')
    return tuple(loads), tuple(solar), tuple(months)


def load_designs(path):
    data = read_json(path)
    require(isinstance(data, list) and data, 'DESIGNS_MUST_BE_NONEMPTY_LIST')
    result=[]
    for d in data:
        require(isinstance(d, dict) and all(k in d for k in ('pv_kw','bess_kwh','pcs_kw')), 'INVALID_DESIGN')
        result.append({k:float(d[k]) for k in ('pv_kw','bess_kwh','pcs_kw')})
    return result


def near(a,b,abs_tol=0.05,rel_tol=1e-8):
    return abs(a-b) <= max(abs_tol,rel_tol*max(abs(a),abs(b)))


# Limites da referencia sintetica em scripts/11_executar_referencia_sintetica.py.
# Nao sao parametros cientificamente homologados.
REFERENCE_BOUNDS = {'pv_kw': (0.0, 1908.225),
                    'bess_kwh': (0.0, 30000.0),
                    'pcs_kw': (0.0, 16500.0)}


def analytical_prefilter(design, epsilon, loads, solar, pcc_limit_kw,
                         bounds=REFERENCE_BOUNDS, c_rate=0.55, tol_kw=1e-6):
    """Condicao necessaria de potencia; PASS nao prova factibilidade temporal."""
    d = {k: float(design[k]) for k in bounds}
    for name, value in d.items():
        if not math.isfinite(value):
            return {'passed': False, 'reason': 'INVALID_NONFINITE_DESIGN', 'variable': name}
        lo, hi = bounds[name]
        if value < lo - 1e-8 or value > hi + 1e-8:
            return {'passed': False, 'reason': 'OUTSIDE_SYNTHETIC_REFERENCE_BOUNDS',
                    'variable': name, 'value': value, 'bounds': [lo, hi]}
    if d['pcs_kw'] > c_rate*d['bess_kwh'] + 1e-8:
        return {'passed': False, 'reason': 'PCS_EXCEEDS_C_RATE',
                'pcs_kw': d['pcs_kw'], 'pcs_max_from_bess_kw': c_rate*d['bess_kwh']}
    if not math.isfinite(epsilon) or epsilon < 0 or epsilon > pcc_limit_kw:
        return {'passed': False, 'reason': 'INVALID_EPSILON'}
    if len(loads) != len(solar) or not loads:
        return {'passed': False, 'reason': 'INVALID_SERIES'}
    worst_kw = -math.inf
    worst_index = None
    for i, (load, pu) in enumerate(zip(loads, solar)):
        residual = load - d['pv_kw']*pu - d['pcs_kw'] - epsilon
        if residual > worst_kw:
            worst_kw, worst_index = residual, i
    return {'passed': worst_kw <= tol_kw,
            'reason': 'NECESSARY_POWER_CHECK_PASS_NOT_SUFFICIENT' if worst_kw <= tol_kw
                      else 'ANALYTICAL_INFEASIBLE_INSTANTANEOUS_POWER',
            'max_power_deficit_kw': max(0.0, worst_kw),
            'worst_interval_index': worst_index,
            'worst_load_kw': loads[worst_index],
            'worst_pv_kw': d['pv_kw']*solar[worst_index],
            'available_pcs_kw': d['pcs_kw'],
            'epsilon_kw': epsilon,
            'min_pcs_kw_at_design_pv': max(0.0, max(
                load - d['pv_kw']*pu - epsilon for load,pu in zip(loads,solar))),
            'note': 'Potencia instantanea apenas; ignora SOC, energia, eficiencia e duracao.'}


def evaluate(design, epsilon, inputs, cfg, econ, contract, prices, evidence, solver, solver_time_limit_seconds=None):
    from d28.optimization.economic_dispatch_f1f2 import solve_economic
    from d28.economics.f1 import annual_bill, present_value, validate_design
    record={'design':design,'epsilon_kw':epsilon,'accepted':False,'reason':None}
    pre=analytical_prefilter(design,epsilon,inputs.load_kw,inputs.pv_pu,cfg.pcc_import_limit_kw)
    record['analytical_prefilter']=pre
    if not pre['passed']:
        record['reason']=pre['reason']
        record['solver_status']='NOT_CALLED_ANALYTICAL_REJECTION'
        return record
    try:
        validate_design(cfg, design['pv_kw'], design['bess_kwh'], design['pcs_kw'])
        require(all(math.isfinite(v) and v>=0 for v in design.values()), 'INVALID_DESIGN')
        result=solve_economic('R0',design,inputs,prices,epsilon_kw=epsilon,
                              months=inputs.months,
                              demand_tariff_brl_kw_month=cfg.demand_tariff_brl_per_kw_month,
                              solver_name=solver, solver_time_limit_seconds=solver_time_limit_seconds)
        record['solver_status']=result.get('status')
        record['solver_state']=result.get('solver_state', 'UNKNOWN')
        record['solver_elapsed_seconds']=result.get('solver_elapsed_seconds')
        record['solver_termination']=result.get('solver_termination',result.get('reason'))
        if result.get('status')!='PASS':
            record['reason']='MILP_NOT_CERTIFIED_OPTIMAL_OR_AUDIT_FAILED'
            record['solver_reason']=result.get('reason')
            return record
        grid=result['grid_kw']
        require(len(grid)==35040, 'ANNUAL_GRID_LENGTH_INVALID')
        bill=annual_bill(cfg,grid,inputs.dt_hours,inputs.months)
        components=result['cost_components_brl']
        require(near(components['grid_brl'],bill['energy_cost_brl']), 'ENERGY_COST_MISMATCH')
        require(near(result['demand_charge_brl'],bill['demand_cost_brl']), 'DEMAND_COST_MISMATCH')
        require(near(result['cost_brl'],bill['total_variable_bill_brl']), 'ANNUAL_BILL_MISMATCH')
        require(near(max(grid),result['pilot_f2_kw'],1e-5), 'F2_MISMATCH')
        require(max(grid)<=epsilon+1e-5, 'EPSILON_VIOLATION')
        require(max(grid)<=cfg.pcc_import_limit_kw+1e-5, 'PCC_VIOLATION')
        pv=present_value(cfg,design['pv_kw'],design['bess_kwh'],design['pcs_kw'],
                         annual_variable_bill_brl=bill['total_variable_bill_brl'],
                         annual_pkm=econ['annual_pkm'])
        require(pv['f1_brl_per_pkm'] is not None and math.isfinite(pv['f1_brl_per_pkm']), 'F1_UNAVAILABLE')
        require(pv['pv_pkm']>0, 'INVALID_PRESENT_VALUE_PKM')
        record.update(accepted=True,reason='PASS_EXPLORATORY_ONLY',
                      f1_brl_per_pkm=pv['f1_brl_per_pkm'],f2_kw=max(grid),
                      annual_grid_kwh=bill['energy_kwh'],
                      annual_bill_brl=bill['total_variable_bill_brl'],
                      milp_cost_brl=result['cost_brl'],
                      economic_delta_brl=result['cost_brl']-bill['total_variable_bill_brl'],
                      pv_total_cost_brl=pv['pv_total_cost_brl'],pv_pkm=pv['pv_pkm'],
                      max_constraint_violation=result.get('max_constraint_violation_native'),
                      checks=result.get('checks'))
        return record
    except Exception as exc:
        record['reason']=f'{type(exc).__name__}: {exc}'
        return record


def nondominated(rows):
    good=[r for r in rows if r['accepted']]
    out=[]
    for i,a in enumerate(good):
        dominated=any(j!=i and b['f1_brl_per_pkm']<=a['f1_brl_per_pkm']+1e-12
                      and b['f2_kw']<=a['f2_kw']+1e-8
                      and (b['f1_brl_per_pkm']<a['f1_brl_per_pkm']-1e-12
                           or b['f2_kw']<a['f2_kw']-1e-8)
                      for j,b in enumerate(good))
        if not dominated: out.append(a)
    return sorted(out,key=lambda r:(r['f2_kw'],r['f1_brl_per_pkm']))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv',required=True,help='CSV anual E100, 35040 linhas')
    p.add_argument('--designs',required=True,help='JSON com lista de desenhos PV/BESS/PCS')
    p.add_argument('--epsilons',nargs='+',type=float,required=True)
    p.add_argument('--out',default='results/REV16_1_4_R0_E100_exploratorio.json')
    p.add_argument('--solver',default='appsi_highs')
    p.add_argument('--solver-time-limit-seconds',type=float,default=None)
    p.add_argument('--max-solves',type=int,default=3,help='Maximo de candidatos, incluindo rejeicoes analiticas')
    p.add_argument('--allow-stale-evidence',action='store_true',help='Registra hashes divergentes; nao homologa')
    args=p.parse_args()
    root=Path.cwd()
    contract_path=root/'config/contrato_sintetico_rev11.json'
    evidence_path=root/'config/annual_f1_f2_evidence.json'
    econ_path=root/'config/economics/r0_f1_exploratory_2026.json'
    contract,evidence,econ=map(read_json,(contract_path,evidence_path,econ_path))
    require(contract['status']=='APPROVED' and contract['scope']=='SYNTHETIC_COUNTERFACTUAL_ONLY','CONTRACT_NOT_APPROVED_FOR_SYNTHETIC')
    require(contract.get('mapping_evidence_status')=='APPROVED','CALENDAR_MAPPING_NOT_APPROVED')
    year=int(contract['year']); mapping=contract.get('source_day_for_calendar_day',{})
    expected={(datetime(year,1,1)+timedelta(days=i)).date().isoformat() for i in range(365)}
    require(set(mapping)==expected,'INCOMPLETE_CALENDAR_MAP')
    require(evidence.get('annual_pkm_approved') is True and
            evidence.get('annual_pkm_approval_scope')=='E100_SYNTHETIC_METHODOLOGICAL_REFERENCE_ONLY', 'E100_PKM_NOT_APPROVED')
    require(econ.get('annual_pkm')==evidence.get('annual_pkm_approved_value')==137675700,'PKM_MISMATCH')
    require(econ.get('status')=='EXPLORATORY_NOT_HOMOLOGATED','UNEXPECTED_ECONOMIC_STATUS')
    # So a tarifa plana e suportada pelo despacho economico atual e annual_bill.
    tariffs=read_json(root/'config/tariffs/rev07_scenarios_exploratory.json')
    flat=next(t for t in tariffs['scenarios'] if t['id']=='FLAT_075_D2500')
    require(flat['model']=='flat' and near(flat['offpeak_brl_kwh'],econ['energy_tariff_brl_per_kwh'],1e-12)
            and near(flat['peak_brl_kwh'],econ['energy_tariff_brl_per_kwh'],1e-12)
            and near(flat['demand_rate_brl_kw_month'],econ['demand_tariff_brl_per_kw_month'],1e-12)
            and near(flat['contracted_demand_kw'],econ['pcc_import_limit_kw'],1e-12),'FLAT_TARIFF_INCONSISTENT')
    require(args.max_solves>0,'INVALID_MAX_SOLVES')
    require(args.solver_time_limit_seconds is None or (math.isfinite(args.solver_time_limit_seconds) and args.solver_time_limit_seconds>0),'INVALID_SOLVER_TIME_LIMIT')
    designs=load_designs(args.designs)
    require(len(designs)*len(args.epsilons)<=args.max_solves,'TOO_MANY_MILP_SOLVES_USE_MAX_SOLVES_EXPLICITLY')
    require(all(math.isfinite(e) and 0<=e<=econ['pcc_import_limit_kw'] for e in args.epsilons),'INVALID_EPSILON')
    hash_diffs=[]
    for group,entries in evidence.get('references',{}).items():
        for entry in entries:
            file=root/entry['path']
            if not file.exists(): hash_diffs.append({'path':entry['path'],'group':group,'status':'MISSING'})
            elif sha(file)!=entry['sha256']: hash_diffs.append({'path':entry['path'],'group':group,'status':'HASH_DIVERGENT'})
    if hash_diffs and not args.allow_stale_evidence:
        print(json.dumps({'status':'BLOCKED_STALE_EVIDENCE','differences':hash_diffs},indent=2,ensure_ascii=False))
        return 2
    from d28.economics.f1 import Economics
    from d28.optimization.biobjective_milp_connector import ConnectorInputs
    from d28.optimization.economic_dispatch_f1f2 import EnergyPrices
    cfg=Economics.from_json(econ_path)
    loads,solar,months=load_inputs(args.csv,year)
    inputs=ConnectorInputs(load_kw=loads,pv_pu=solar,months=months,dt_hours=0.25,
                           pcc_cap_kw=cfg.pcc_import_limit_kw,terminal_policy='cyclic')
    prices=EnergyPrices(grid_brl_kwh=(cfg.energy_tariff_brl_per_kwh,)*len(loads))
    records=[]
    for design in designs:
        for eps in args.epsilons:
            print(f'R0/E100: PV={design["pv_kw"]} BESS={design["bess_kwh"]} PCS={design["pcs_kw"]} epsilon={eps}',flush=True)
            rec=evaluate(design,eps,inputs,cfg,econ,contract,prices,evidence,args.solver,args.solver_time_limit_seconds)
            records.append(rec)
            print('  ',rec['reason'],flush=True)
            # Checkpoint apos cada MILP
            write_report(args.out,records,hash_diffs,args,contract_path,evidence_path,econ_path)
    return 0


def write_report(path,records,hash_diffs,args,contract_path,evidence_path,econ_path):
    dest=Path(path); dest.parent.mkdir(parents=True,exist_ok=True)
    report={'revision':'REV16.1.4','scope':'R0_E100_SYNTHETIC_EXPLORATORY_ONLY',
            'method':'EPSILON_SWEEP_NOT_NSGA2','scientific_homologation':False,
            'analytical_prefilter':'NECESSARY_INSTANTANEOUS_POWER_ONLY',
            'reference_bounds':REFERENCE_BOUNDS,
            'reference_bounds_source':'scripts/11_executar_referencia_sintetica.py:24',
            'reference_bounds_homologated':False,
            'status':'EXPLORATORY_WITH_STALE_EVIDENCE' if hash_diffs else 'EXPLORATORY_NOT_HOMOLOGATED',
            'tariff':'FLAT_075_D2500','demand_convention':'MONTHLY_MEASURED_PEAK_NOT_CONTRACTED_MINIMUM',
            'contract_sha256':sha(contract_path),'evidence_sha256':sha(evidence_path),
            'economics_sha256':sha(econ_path),'csv_sha256':sha(args.csv),
            'designs_sha256':sha(args.designs),'hash_discrepancies':hash_diffs,
            'evaluations':records,'nondominated_exploratory':nondominated(records),
            'accepted_count':sum(r['accepted'] for r in records)}
    tmp=dest.with_suffix(dest.suffix+'.tmp')
    tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    tmp.replace(dest)

if __name__=='__main__':
    try: sys.exit(main())
    except Exception as exc:
        print(f'PREFLIGHT_BLOCKED: {type(exc).__name__}: {exc}',file=sys.stderr)
        sys.exit(2)
