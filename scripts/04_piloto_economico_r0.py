"""REV04: um candidato R0, quatro intervalos, despacho economico sob epsilon.
Nao calcula F1 anual, nao executa GA e nao altera equacoes fisicas.
"""
from __future__ import annotations
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import pyomo.environ as p
from d28.optimization.biobjective_milp_connector import ConnectorInputs, build_route_milp, solve_peak_then_energy

LOAD=(100.,150.,120.,80.)
PV_PU=(0.,.3,.5,.1)
DESIGN={'pv_kw':100.,'bess_kwh':500.,'pcs_kw':100.}
DT=.25
# Tarifa ilustrativa, NAO proveniente da Base Mestre e NAO homologada.
TARIFF=(.50,.90,1.20,.60)

def make_model():
    inputs=ConnectorInputs(load_kw=LOAD,pv_pu=PV_PU,dt_hours=DT,
                           pcc_cap_kw=2500.,terminal_policy='cyclic',route_options={})
    return build_route_milp('R0',DESIGN,inputs)

def audit_constraints(m):
    worst=0.; name=None; count=0
    for c in m.component_data_objects(p.Constraint,active=True,descend_into=True):
        v=p.value(c.body,exception=False)
        if v is None or not math.isfinite(float(v)):
            raise RuntimeError('CONSTRAINT_VALUE_MISSING: '+c.name)
        err=0.
        if c.has_lb(): err=max(err,float(p.value(c.lower))-float(v))
        if c.has_ub(): err=max(err,float(v)-float(p.value(c.upper)))
        if err>worst: worst,name=err,c.name
        count+=1
    return {'count':count,'max_violation_native_units':worst,'worst_constraint':name}

def grid_metrics(m):
    grid=[float(p.value(m.grid[t])) for t in m.T]
    return {'grid_kw':grid,'pilot_peak_kw':max(grid),
            'grid_energy_kwh':DT*sum(grid),
            'pilot_energy_cost_brl':DT*sum(TARIFF[i]*g for i,g in enumerate(grid)),
            'bess_initial_kwh':float(p.value(m.bess_energy[0])),
            'bess_terminal_kwh':float(p.value(m.bess_energy[len(grid)])),
            'constraints':audit_constraints(m)}

def run(epsilon_margin_kw=20., tolerance=1e-5):
    if not math.isfinite(epsilon_margin_kw) or epsilon_margin_kw < 0:
        raise ValueError('epsilon margin must be nonnegative and finite')
    baseline=make_model()
    baseline_solve=solve_peak_then_energy(baseline,dt_hours=DT,solver_name='appsi_highs')
    if not baseline_solve['optimal']:
        raise RuntimeError('BASELINE_NOT_OPTIMAL')
    baseline_metrics=grid_metrics(baseline)
    epsilon_kw=float(baseline_solve['audit']['optimal_peak_kw'])+epsilon_margin_kw
    m=make_model()
    # Apenas restricao epsilon e objetivo de custo sao ADICIONADOS.
    # Todas as equacoes fisicas do construtor permanecem intactas.
    m.rev04_epsilon_peak=p.Constraint(m.T,rule=lambda model,t: model.grid[t] <= epsilon_kw)
    for obj in m.component_data_objects(p.Objective,active=True,descend_into=True):
        obj.deactivate()
    m.rev04_energy_cost_brl=p.Expression(expr=DT*sum(TARIFF[i]*m.grid[t] for i,t in enumerate(m.T)))
    m.rev04_cost_objective=p.Objective(expr=m.rev04_energy_cost_brl,sense=p.minimize)
    solver=p.SolverFactory('appsi_highs')
    if not solver.available(False): raise RuntimeError('HIGHS_UNAVAILABLE')
    result=solver.solve(m,tee=False)
    if result.solver.termination_condition != p.TerminationCondition.optimal:
        raise RuntimeError('ECONOMIC_TERMINATION_'+str(result.solver.termination_condition))
    econ=grid_metrics(m)
    econ['objective_value_brl']=float(p.value(m.rev04_energy_cost_brl))
    econ['epsilon_residual_kw']=max(0.,econ['pilot_peak_kw']-epsilon_kw)
    econ['cost_identity_residual_brl']=abs(econ['objective_value_brl']-econ['pilot_energy_cost_brl'])
    checks={
        'epsilon_peak':econ['epsilon_residual_kw']<=tolerance,
        'physical_constraints':econ['constraints']['max_violation_native_units']<=tolerance,
        'cyclic_bess':abs(econ['bess_initial_kwh']-econ['bess_terminal_kwh'])<=tolerance,
        'objective_identity':econ['cost_identity_residual_brl']<=tolerance,
        'nonnegative_grid':min(econ['grid_kw'])>=-tolerance,
        'economic_not_worse_than_baseline_under_epsilon':econ['pilot_energy_cost_brl']<=baseline_metrics['pilot_energy_cost_brl']+tolerance,
    }
    return {'protocol':'D28_REV04_CONTROLLED_ECONOMIC_PILOT','generated_utc':datetime.now(timezone.utc).isoformat(),
            'route':'R0','candidate':DESIGN,'intervals':4,'dt_hours':DT,
            'input_origin':'SYNTHETIC_SMOKE_TEST_NOT_HOMOLOGATED',
            'tariff_origin':'ILLUSTRATIVE_NON_HOMOLOGATED','tariff_brl_per_kwh':TARIFF,
            'objective':'MIN_SUM_INTERVAL_GRID_ENERGY_COST_BRL',
            'epsilon_peak_kw':epsilon_kw,'epsilon_margin_kw':epsilon_margin_kw,
            'f1_annual_brl_per_pkm':None,'annual_accounting_performed':False,
            'f3_excluded':True,'nsga2_executed':False,'physical_equations_modified':False,
            'annual_economic_adapter_used':False,'baseline_lexicographic':baseline_metrics,
            'economic_epsilon':econ,'checks':checks,
            'status':'PASS' if all(checks.values()) else 'FAILED',
            'limitations':['No demand-charge model or monthly billing in four intervals',
                           'No CHP fuel or gas costs: R0 only',
                           'Illustrative time-varying energy tariff, not validated',
                           'Pilot cost is not annual F1 or a Pareto frontier']}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='results/rev04_piloto_economico_r0.json')
    parser.add_argument('--epsilon-margin-kw',type=float,default=20.)
    args=parser.parse_args()
    report=run(args.epsilon_margin_kw)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print('R0:',report['status'],'| baseline_cost=',round(report['baseline_lexicographic']['pilot_energy_cost_brl'],6),
          '| economic_cost=',round(report['economic_epsilon']['pilot_energy_cost_brl'],6),
          '| epsilon_kw=',round(report['epsilon_peak_kw'],6))
    print('Auditoria:',path)
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
