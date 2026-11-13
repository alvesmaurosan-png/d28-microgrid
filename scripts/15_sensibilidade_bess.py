"""REV15 — sensibilidade de energia BESS com PCS fixo, LP + certificacao binaria.
Execute na raiz do repositorio. Nao altera arquivos existentes.
"""
import argparse, csv, hashlib, json, math, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import pyomo.environ as p
from pyomo.contrib.appsi.solvers import Highs
from d28.optimization.synthetic_reference_rev11 import load_reference, read_json
from d28.optimization.biobjective_milp_connector import build_route_milp


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--scenario',default='E100')
    ap.add_argument('--bess-kwh',type=float,required=True)
    ap.add_argument('--pcs-kw',type=float,default=5500.)
    ap.add_argument('--time-limit',type=float,default=900)
    ap.add_argument('--tolerance',type=float,default=1e-5)
    a=ap.parse_args()
    settings=read_json(ROOT/'config'/'synthetic_reference_rev11.json')
    _,inputs,_,_,_,_,provenance=load_reference(ROOT,a.scenario,'R0',settings)
    design={'pv_kw':1908.225,'bess_kwh':a.bess_kwh,'pcs_kw':a.pcs_kw}
    if a.bess_kwh<=0 or a.pcs_kw<=0: raise SystemExit('BESS e PCS devem ser positivos')
    m=build_route_milp('R0',design,inputs)
    n=len(inputs.load_kw); dt=float(inputs.dt_hours)
    # Retirar exclusivamente o teto de importacao da rede.
    for t in m.T:
        m.grid[t].setub(None)
        m.bess_mode[t].domain=p.UnitInterval
    for o in m.component_data_objects(p.Objective,active=True):o.deactivate()
    m.rev14_peak=p.Var(domain=p.NonNegativeReals)
    m.rev14_cap=p.Constraint(m.T,rule=lambda mm,t:mm.grid[t]<=mm.rev14_peak)
    m.rev14_obj=p.Objective(expr=m.rev14_peak,sense=p.minimize)
    solver=Highs();solver.config.load_solution=False;solver.config.time_limit=a.time_limit
    result=solver.solve(m)
    termination=str(result.termination_condition).split('.')[-1].lower()
    if termination!='optimal':
        print('LP_NOT_OPTIMAL:',result.termination_condition)
        raise SystemExit(2)
    solver.load_vars()
    lower_bound=float(result.best_objective_bound)
    lp_peak=float(p.value(m.rev14_peak))
    tol=a.tolerance
    before_fractional=sum(tol<float(p.value(m.bess_mode[t]))<1-tol for t in m.T)
    both=[]; mode_changes=0
    # Congelar apenas o modo; nenhuma potencia ou energia e alterada.
    for t in m.T:
        c=float(p.value(m.bess_charge[t])); d=float(p.value(m.bess_discharge[t]))
        if c>tol and d>tol:both.append(int(t))
        z=1 if c>tol else 0
        if abs(float(p.value(m.bess_mode[t]))-z)>tol:mode_changes+=1
        m.bess_mode[t].set_value(z);m.bess_mode[t].fix()
    # Checagem de TODAS as restricoes ativas e dos limites das variaveis.
    failures=[];checked=0;worst=0.;worst_name=''
    def check(name,viol):
        nonlocal checked,worst,worst_name
        checked+=1
        if not math.isfinite(viol):raise RuntimeError('Nao finito: '+name)
        if viol>worst:worst=viol;worst_name=name
        if viol>tol and len(failures)<30:failures.append({'name':name,'violation':viol})
    for con in m.component_data_objects(p.Constraint,active=True,descend_into=True):
        b=float(p.value(con.body));v=0.
        if con.has_lb():v=max(v,float(p.value(con.lower))-b)
        if con.has_ub():v=max(v,b-float(p.value(con.upper)))
        check(con.name,max(0.,v))
    for var in m.component_data_objects(p.Var,descend_into=True):
        x=float(p.value(var));v=0.
        if var.has_lb():v=max(v,float(p.value(var.lb))-x)
        if var.has_ub():v=max(v,x-float(p.value(var.ub)))
        check(var.name,max(0.,v))
    actual_peak=max(float(p.value(m.grid[t])) for t in m.T)
    objective=float(p.value(m.rev14_obj))
    gap=objective-lower_bound
    certified=(not both and worst<=tol and abs(gap)<=tol and abs(actual_peak-lp_peak)<=tol)
    src=ROOT/'data'/'processed'/'milp_inputs'/f'R0_inputs_{a.scenario}_15min.csv'
    with src.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    if len(rows)!=n:raise RuntimeError('Inconsistencia no tamanho da serie CSV')
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    expected=provenance.get('series',{}).get('sha256')
    if expected and digest!=expected:raise RuntimeError('SHA256 das entradas divergente')
    out=ROOT/'results';out.mkdir(exist_ok=True)
    stem=f'rev15_limiar_pcc_{a.scenario}_BESS{a.bess_kwh:g}_PCS{a.pcs_kw:g}'
    csvpath=out/(stem+'_dispatch.csv')
    fields=['interval_index','interval_start_local','load_kw','pv_available_kw','pv_used_kw','grid_kw','charge_kw','discharge_kw','soc_kwh','soc_next_kwh','mode_binary','peak_margin_kw']
    with csvpath.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for t in range(n):
            grid=float(p.value(m.grid[t]));w.writerow(dict(interval_index=t,interval_start_local=rows[t]['interval_start_local'],load_kw=float(inputs.load_kw[t]),pv_available_kw=float(inputs.pv_pu[t])*design['pv_kw'],pv_used_kw=float(p.value(m.pv[t])),grid_kw=grid,charge_kw=float(p.value(m.bess_charge[t])),discharge_kw=float(p.value(m.bess_discharge[t])),soc_kwh=float(p.value(m.bess_energy[t])),soc_next_kwh=float(p.value(m.bess_energy[t+1])),mode_binary=int(round(float(p.value(m.bess_mode[t])))),peak_margin_kw=lp_peak-grid))
    report=dict(status='CERTIFIED_MINIMUM_PCC' if certified else 'LP_LOWER_BOUND_ONLY_NOT_CERTIFIED',scenario=a.scenario,route='R0',annual_intervals=n,dt_hours=dt,design=design,original_pcc_cap_kw=float(inputs.pcc_cap_kw),lp_optimal_peak_kw=lp_peak,lp_lower_bound_kw=lower_bound,converted_actual_peak_kw=actual_peak,objective_gap_kw=gap,mode_changes=mode_changes,fractional_modes_lp=before_fractional,simultaneous_intervals_lp=len(both),simultaneous_first_30=both[:30],checks_performed=checked,max_violation=worst,worst_violation_name=worst_name,violations_first_30=failures,annual_grid_energy_kwh=dt*sum(float(p.value(m.grid[t])) for t in m.T),annual_load_kwh=dt*sum(inputs.load_kw),source_sha256=digest,method='Single annual LP minimax peak + binary conversion and full active constraint/bound validation. No MILP.',limitations='Fixed design and original synthetic E100 load; minimum PCC for this design only. Not F1/F2 Pareto. If not certified, LP value is only a lower bound.')
    reportpath=out/(stem+'_validacao.json')
    reportpath.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('STATUS:',report['status'])
    print('MINIMUM PCC LP (kW):',round(lp_peak,9))
    print('LP lower bound (kW):',round(lower_bound,9))
    print('Annual constraints and variable bounds checked:',checked,'max violation:',worst)
    print('Fractional modes in LP:',before_fractional,'converted:',mode_changes,'simultaneous:',len(both))
    print('Annual grid energy (kWh):',round(report['annual_grid_energy_kwh'],3))
    print('VALIDATION:',reportpath)
    print('DISPATCH:',csvpath)
    if not certified:raise SystemExit(3)

if __name__=='__main__':main()
