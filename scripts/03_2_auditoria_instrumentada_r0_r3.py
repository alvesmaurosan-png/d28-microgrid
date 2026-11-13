"""REV03.2: instrumentacao de leitura do MILP, sem alterar equacoes ou GA.
Reexecuta os quatro candidatos sinteticos da REV03 e produz trilhas de auditoria.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import pyomo.environ as p
from d28.optimization.biobjective_milp_connector import ConnectorInputs, build_route_milp, solve_peak_then_energy

LOAD=(100.,150.,120.,80.)
PV_PU=(0.,.3,.5,.1)
DESIGN={'pv_kw':100.,'bess_kwh':500.,'pcs_kw':100.}
CHP={'chp_capacity_kw':80.,'electrical_efficiency':.35,'fuel_lhv_kwh_per_nm3':10.,'availability':(1,1,1,1)}
OPTIONS={'R0':{},'R1':dict(CHP),'R2':{**CHP,'production_nm3':(10.,)*4,'gasometer_capacity_nm3':200.,'initial_gas_nm3':100.,'auxiliary_kw':(2.,)*4,'terminal_gas_policy':'cyclic'},'R3':{**CHP,'cgob_coverage_nm3':0.}}

def val(x):
    y=p.value(x,exception=False)
    if y is None or not math.isfinite(float(y)):
        raise ValueError(f'NONFINITE_OR_MISSING: {getattr(x,"name",str(x))}')
    return float(y)

def residuals(model):
    worst={'value':0.,'name':None,'unit':'native'}
    count=0
    for c in model.component_data_objects(p.Constraint,active=True,descend_into=True):
        b=val(c.body); v=0.
        if c.has_lb(): v=max(v,val(c.lower)-b)
        if c.has_ub(): v=max(v,b-val(c.upper))
        count+=1
        if v>worst['value']: worst={'value':v,'name':c.name,'unit':'native'}
    return {'count':count,'worst':worst}

def analyze(route,tol):
    dt=.25; n=len(LOAD)
    inputs=ConnectorInputs(load_kw=LOAD,pv_pu=PV_PU,dt_hours=dt,pcc_cap_kw=2500.,terminal_policy='cyclic',route_options=OPTIONS[route])
    out={'route':route,'input_origin':'SYNTHETIC_SMOKE_TEST_NOT_HOMOLOGATED','candidate':DESIGN,'intervals':n,'dt_hours':dt,'f1':None,'f3_excluded':True,'nsga2_executed':False,'checks':{}}
    try:
        m=build_route_milp(route,DESIGN,inputs)
        solved=solve_peak_then_energy(m,dt_hours=dt,solver_name='appsi_highs')
        out['solver']=solved['audit']
        if not solved['optimal']:
            out.update(status='FAILED',reason='MILP_NOT_OPTIMAL'); return out
        tlist=list(m.T)
        states=[val(m.bess_energy[t]) for t in range(n+1)]
        cap=DESIGN['bess_kwh']*float(m._r0_metadata.get('soh',1.))
        # A equacao existente utiliza eta_charge=eta_discharge=0.922 por padrao.
        # Nao se presume que essa configuracao vale para outros experimentos.
        eta_c=.922; eta_d=.922
        trace=[]; errs={'electric_kw':[],'bess_kwh':[],'pv_kw':[],'chp_kwh':[],'gas_nm3':[]}
        gas=[val(m.gas_stock[t]) for t in range(n+1)] if hasattr(m,'gas_stock') else None
        for i,t in enumerate(tlist):
            grid=val(m.grid[t]); load=val(m.load_kw[t]); pv=val(m.pv[t]); curt=val(m.pv_curt[t]); charge=val(m.bess_charge[t]); discharge=val(m.bess_discharge[t]); mode=val(m.bess_mode[t]); auxiliary=val(m.auxiliary_load_kw[t]) if hasattr(m,'auxiliary_load_kw') else 0.
            gross=val(m.chp.power_gross_kw[t]) if hasattr(m,'chp') else 0.
            fuel=val(m.chp.fuel_nm3[t]) if hasattr(m,'chp') else 0.
            electric=grid+pv+discharge+gross-load-charge-auxiliary
            bess=states[i+1]-states[i]-eta_c*charge*dt+discharge*dt/eta_d
            solar=pv+curt-DESIGN['pv_kw']*PV_PU[i]
            chp=gross*dt-CHP['electrical_efficiency']*CHP['fuel_lhv_kwh_per_nm3']*fuel if hasattr(m,'chp') else 0.
            entry={'interval':i,'grid_kw':grid,'load_kw':load,'pv_used_kw':pv,'pv_curtailment_kw':curt,'bess_charge_kw':charge,'bess_discharge_kw':discharge,'bess_mode':mode,'bess_energy_initial_kwh':states[i],'bess_energy_final_kwh':states[i+1],'bess_soc_initial':states[i]/cap if cap else None,'bess_soc_final':states[i+1]/cap if cap else None,'chp_gross_kw':gross,'chp_fuel_nm3_per_interval':fuel,'auxiliary_load_kw':auxiliary,'residual_electric_kw':electric,'residual_bess_kwh':bess,'residual_pv_kw':solar,'residual_chp_kwh':chp}
            for key,v in [('electric_kw',electric),('bess_kwh',bess),('pv_kw',solar),('chp_kwh',chp)]:errs[key].append(abs(v))
            if gas is not None:
                production=float(OPTIONS[route]['production_nm3'][i]); loss=val(m.gas_loss[t]); gas_err=gas[i+1]-gas[i]-production+fuel+loss
                entry.update(gas_stock_initial_nm3=gas[i],gas_stock_final_nm3=gas[i+1],gas_production_nm3_per_interval=production,gas_loss_nm3_per_interval=loss,residual_gas_nm3=gas_err)
                errs['gas_nm3'].append(abs(gas_err))
            trace.append(entry)
        check={
            'electric_balance':max(errs['electric_kw'])<=tol,
            'bess_transition':max(errs['bess_kwh'])<=tol,
            'pv_accounting':max(errs['pv_kw'])<=tol,
            'bess_cyclic_terminal':abs(states[-1]-states[0])<=tol,
            'bess_soc_bounds':all(.1-tol<=s/cap<=.9+tol for s in states),
            'bess_no_simultaneous_charge_discharge':all(min(e['bess_charge_kw'],e['bess_discharge_kw'])<=tol for e in trace),
            'pcs_power_bounds':all(e['bess_charge_kw']<=DESIGN['pcs_kw']+tol and e['bess_discharge_kw']<=DESIGN['pcs_kw']+tol for e in trace),
            'pcc_bounds':all(-tol<=e['grid_kw']<=inputs.pcc_cap_kw+tol for e in trace),
            'all_active_constraints':residuals(m)['worst']['value']<=tol,
        }
        if hasattr(m,'chp'):
            check['chp_fuel_energy_consistency']=max(errs['chp_kwh'])<=tol
            check['chp_capacity_and_availability']=all(e['chp_gross_kw']<=CHP['chp_capacity_kw']*CHP['availability'][i]+tol for i,e in enumerate(trace))
        if gas is not None:
            check['gas_transition']=max(errs['gas_nm3'])<=tol
            check['gas_cyclic_terminal']=abs(gas[-1]-gas[0])<=tol
            check['gas_stock_bounds']=all(-tol<=s<=OPTIONS[route]['gasometer_capacity_nm3']+tol for s in gas)
        out['checks']=check
        out['maximum_residuals']={k:max(v) if v else None for k,v in errs.items()}
        out['constraints']=residuals(m)
        out['boundary_conditions']={'bess_initial_kwh':states[0],'bess_terminal_kwh':states[-1],'bess_initial_soc':states[0]/cap,'bess_terminal_soc':states[-1]/cap,'bess_terminal_policy':'cyclic','gas_initial_nm3':gas[0] if gas else None,'gas_terminal_nm3':gas[-1] if gas else None,'gas_terminal_policy':'cyclic' if gas else None,'gas_capacity_nm3':OPTIONS[route].get('gasometer_capacity_nm3')}
        out['aggregates']={'grid_energy_kwh':sum(e['grid_kw'] for e in trace)*dt,'pilot_f2_peak_kw':max(e['grid_kw'] for e in trace),'pv_energy_kwh':sum(e['pv_used_kw'] for e in trace)*dt,'bess_charge_energy_kwh':sum(e['bess_charge_kw'] for e in trace)*dt,'bess_discharge_energy_kwh':sum(e['bess_discharge_kw'] for e in trace)*dt,'chp_gross_energy_kwh':sum(e['chp_gross_kw'] for e in trace)*dt,'chp_fuel_nm3':sum(e['chp_fuel_nm3_per_interval'] for e in trace),'gas_production_nm3':sum(e.get('gas_production_nm3_per_interval',0.) for e in trace),'gas_loss_nm3':sum(e.get('gas_loss_nm3_per_interval',0.) for e in trace)}
        out['trace']=trace
        out['status']='PASS' if all(check.values()) else 'FAILED'
        out['reason']='ALL_INSTRUMENTED_CHECKS_OK' if out['status']=='PASS' else 'AUDIT_CHECK_FAILED'
    except Exception as exc:
        out.update(status='ERROR',reason=f'{type(exc).__name__}: {exc}')
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='results/rev03_2_auditoria_instrumentada_r0_r3.json')
    parser.add_argument('--tolerance',type=float,default=1e-5)
    args=parser.parse_args()
    if not 0<args.tolerance<=1e-2:parser.error('tolerance must be in (0,1e-2]')
    report={'protocol':'D28_REV03_2_INSTRUMENTED_PHYSICAL_PILOT','generated_utc':datetime.now(timezone.utc).isoformat(),'dispatch_policy':'MIN_PEAK_THEN_MIN_GRID_ENERGY','dispatch_is_f1_optimal':False,'annual_accounting_performed':False,'population_executed':False,'synthetic_test_only':True,'tolerance':args.tolerance,'model_equations_modified':False,'notes':['CHP fuel is Nm3 per interval, not Nm3/h','R2 production and gas loss are Nm3 per interval','R3 CGOB is accounting attribute; not a physical gasometer','BESS efficiency values .922 are existing builder defaults; confirm if defaults change'],'results':[analyze(route,args.tolerance) for route in ('R0','R1','R2','R3')]}
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    for r in report['results']:
        print(f"{r['route']}: {r['status']} | {r['reason']} | checks={len(r['checks'])} | F2_piloto={r.get('aggregates',{}).get('pilot_f2_peak_kw','N/A')} kW")
    print('Auditoria:',path)
    return 0 if all(r['status']=='PASS' for r in report['results']) else 1
if __name__=='__main__':raise SystemExit(main())
