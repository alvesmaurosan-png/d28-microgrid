"""REV13.3: valida os 35040 intervalos LP, sem executar MILP inteiro."""
import argparse, csv, hashlib, importlib.util, json, sys, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import pyomo.environ as p
from pyomo.contrib.appsi.solvers import Highs
from d28.optimization.synthetic_reference_rev11 import load_reference, read_json

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--scenario',default='E100')
    ap.add_argument('--window',type=int,default=8)
    ap.add_argument('--policy',choices=['physical','protect-pcc'],default='physical')
    ap.add_argument('--time-limit',type=float,default=600)
    a=ap.parse_args()
    if a.window<0: ap.error('window must be nonnegative')
    rev12=ROOT/'scripts'/'12_diagnostico_relaxacao_r0.py'
    if not rev12.exists():raise FileNotFoundError(rev12)
    spec=importlib.util.spec_from_file_location('d28_rev12_diag',rev12)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    settings=read_json(ROOT/'config/synthetic_reference_rev11.json')
    _,inputs,_,_,_,_,provenance=load_reference(ROOT,a.scenario,'R0',settings)
    design={'pv_kw':1908.225,'bess_kwh':10000.,'pcs_kw':5500.}
    m,weights=module.build_diagnostic(inputs,design,integer=False,policy=a.policy)
    solver=Highs();solver.config.load_solution=False;solver.config.time_limit=a.time_limit
    res=solver.solve(m)
    if str(res.termination_condition).split('.')[-1].lower() != 'optimal':
        raise RuntimeError(f'LP not optimal: {res.termination_condition}; no exports written')
    solver.load_vars()
    d=m.diag; dt=float(inputs.dt_hours)
    # Columnas do CSV original; nao inferir timestamps por posicao.
    src=ROOT/'data'/'processed'/'milp_inputs'/f'R0_inputs_{a.scenario}_15min.csv'
    with src.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    if len(rows)!=len(inputs.load_kw):raise RuntimeError('CSV length mismatch')
    actual_hash=hashlib.sha256(src.read_bytes()).hexdigest()
    expected_hash=provenance.get('series',{}).get('sha256')
    if expected_hash and actual_hash!=expected_hash:raise RuntimeError('CSV SHA256 mismatch')
    n=len(rows)
    critical=[t for t in range(n) if p.value(d.pcc[t])>1e-5]
    selection=set(range(n))  # REV13.3: exportacao anual integral
    output=[];simultaneous=[];max_balance=0.
    for t in range(n):
        grid=float(p.value(m.grid[t])); charge=float(p.value(m.bess_charge[t])); discharge=float(p.value(m.bess_discharge[t]));pv=float(p.value(m.pv[t]));mode=float(p.value(m.bess_mode[t]));slack=float(p.value(d.pcc[t]));soc=float(p.value(m.bess_energy[t]));soc_next=float(p.value(m.bess_energy[t+1]));load=float(inputs.load_kw[t]);deficit=float(p.value(d.deficit[t]));surplus=float(p.value(d.surplus[t]))
        residual=grid+pv+discharge+deficit-load-charge-surplus
        max_balance=max(max_balance,abs(residual))
        if charge>1e-5 and discharge>1e-5:simultaneous.append(t)
        if t in selection:
            row=rows[t]
            output.append({'interval_index':t,'interval_start_local':row['interval_start_local'],'load_kw':load,'pv_available_kw':float(row['pv_kw_per_kwp'])*design['pv_kw'],'P_grid_kw':grid,'P_charge_kw':charge,'P_discharge_kw':discharge,'SOC_kwh':soc,'SOC_next_kwh':soc_next,'PV_used_kw':pv,'bess_mode_lp':mode,'PCC_slack_kw':slack,'deficit_kw':deficit,'surplus_kw':surplus,'soc_low_slack_kwh':float(p.value(d.soc_low[t])),'soc_high_slack_kwh':float(p.value(d.soc_high[t])),'balance_residual_kw':residual,'critical':t in critical})
    # Fixar o modo sem alterar nenhuma outra variavel da solucao LP.
    # A regra z=1 em carga e z=0 em descarga respeita a convencao da REV12.
    tol=1e-6
    fractional_before=sum(1 for t in range(n) if tol<float(p.value(m.bess_mode[t]))<1-tol)
    mode_changed=0
    for t in range(n):
        c=float(p.value(m.bess_charge[t])); q=float(p.value(m.bess_discharge[t]))
        if c>tol and q>tol:
            raise RuntimeError(f'Carga e descarga simultaneas em t={t}; conversao nao certificavel')
        new_mode=1 if c>tol else 0
        old_mode=float(p.value(m.bess_mode[t]))
        mode_changed+=abs(old_mode-new_mode)>tol
        m.bess_mode[t].set_value(new_mode)
        m.bess_mode[t].fix()
    # Verificacao integral: todas as restricoes ativas, inclusive as de modo,
    # diagnostico, SOC, PCS, PV, balanco e terminal.
    failures=[]; worst=0.; checked=0; worst_name=None
    for con in m.component_data_objects(p.Constraint,active=True,descend_into=True):
        if not con.active: continue
        checked+=1
        body=float(p.value(con.body))
        if not math.isfinite(body): raise RuntimeError(f'Valor nao finito: {con.name}')
        violation=0.
        if con.has_lb(): violation=max(violation,float(p.value(con.lower))-body)
        if con.has_ub(): violation=max(violation,body-float(p.value(con.upper)))
        violation=max(0.,violation)
        if violation>worst: worst=violation;worst_name=con.name
        if violation>tol and len(failures)<30:failures.append({'constraint':con.name,'violation':violation})
    objective_after=float(p.value(d.objective))
    objective_before=float(res.best_objective_bound)
    gap=abs(objective_after-objective_before)
    certified=not failures and worst<=tol and gap<=tol
    # Atualizar coluna exportada para mostrar tambem modo convertido.
    for item in output:
        t=int(item['interval_index'])
        item['bess_mode_binary']=int(round(float(p.value(m.bess_mode[t]))))
    validation={
        'status':'CERTIFIED_DIAGNOSTIC_MILP_OPTIMUM' if certified else 'NOT_CERTIFIED',
        'scope':'R0 E100 REV12 diagnostic physical with slack, NOT original hard-PCC model',
        'annual_intervals':n,'constraints_checked':checked,
        'fractional_modes_lp':fractional_before,'mode_values_changed':mode_changed,
        'binary_modes_after':True,'simultaneous_charge_discharge':len(simultaneous),
        'max_constraint_violation':worst,'worst_constraint':worst_name,
        'violations_first_30':failures,
        'lp_lower_bound':objective_before,'binary_feasible_objective':objective_after,
        'objective_gap':gap,'pcc_slack_kwh':sum(float(p.value(d.pcc[t]))*dt for t in range(n)),
        'important_limitation':'Does not establish feasibility of the original model without slacks; not valid for F1/F2',
        'source_csv_sha256':actual_hash,
    }
    target=ROOT/'results';target.mkdir(exist_ok=True)
    val_path=target/f'rev13_3_validacao_anual_{a.scenario}_{a.policy}.json'
    val_path.write_text(json.dumps(validation,indent=2,ensure_ascii=False),encoding='utf-8')
    print('REV13.3 annual validation:',validation['status'])
    print('Constraints checked:',checked,'maximum violation:',worst)
    print('Modes changed:',mode_changed,'objective gap:',gap)
    print('VALIDATION:',val_path)

    csv_path=target/f'rev13_3_dispatch_anual_{a.scenario}_{a.policy}.csv'
    with csv_path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(output[0]) if output else ['interval_index']);w.writeheader();w.writerows(output)
    report={'status':'LP_OPTIMAL','scenario':a.scenario,'policy':a.policy,'intervals':n,'critical_indices':critical,'critical_count':len(critical),'critical_pcc_kwh':sum(float(p.value(d.pcc[t]))*dt for t in critical),'max_pcc_slack_kw':max((float(p.value(d.pcc[t])) for t in critical),default=0.),'simultaneous_charge_discharge_count':len(simultaneous),'simultaneous_indices_first_100':simultaneous[:100],'fractional_mode_count':sum(1 for t in range(n) if 1e-5<float(p.value(m.bess_mode[t]))<1-1e-5),'max_balance_residual_kw':max_balance,'solver_objective':float(p.value(d.objective)),'solver_bound':res.best_objective_bound,'csv_sha256':actual_hash,'source_rev12':str(rev12.relative_to(ROOT)),'not_valid_for_f1_f2':True,'interpretation':'LP_DIAGNOSTIC_ONLY','binary_validation':validation}
    json_path=target/f'rev13_3_dispatch_anual_{a.scenario}_{a.policy}.json';json_path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('LP OPTIMAL; no integer MILP executed; full-year export and binary validation')
    print('Critical indices:',critical)
    print('PCC slack energy kWh:',round(report['critical_pcc_kwh'],5))
    print('Simultaneous charge/discharge intervals:',len(simultaneous))
    print('Fractional mode intervals:',report['fractional_mode_count'])
    print('Max balance residual kW:',max_balance)
    print('CSV:',csv_path);print('REPORT:',json_path)
if __name__=='__main__':main()
