"""REV05.2: despacho físico condicionado, sem cálculo de F1/F3."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from d28.traceability.physical_parameterization import parameterize_physical
from d28.traceability.physical_rev052 import conditional_r2_sizing
from d28.traceability.r2_closure import verify_rev09_charging_boundary
from d28.optimization.r0_r3_bridge import build_architecture, solve_highs
from validar_d28_dia_fonte_r0_r3 import source_day,COMMON_DESIGN,CHP_DESIGN,CONTRACT
import pyomo.environ as p
BASE=ROOT/'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'

def run():
    if json.loads(CONTRACT.read_text(encoding='utf-8-sig')).get('status')=='APPROVED':
        raise RuntimeError('Somente execução condicionada sem contrato anual aprovado')
    boundary=verify_rev09_charging_boundary(
        ROOT/'data/raw/demanda/D28_REV09_demanda_15min.csv',
        ROOT/'scripts/gerar_calendario_anual.py')
    load,pv,solar_status=source_day('E100',0)
    params=parameterize_physical(BASE,common=COMMON_DESIGN,chp=CHP_DESIGN)
    common=dict(params['common'],load_kw=load,pv_pu=pv)
    chp_routes=params['chp_by_route']
    sizing=conditional_r2_sizing(BASE,substrate_t_per_day=10.,
        chp_capacity_kw=chp_routes['R2']['chp_capacity_kw'],
        electrical_efficiency=chp_routes['R2']['electrical_efficiency'],
        fuel_lhv_kwh_per_nm3=chp_routes['R2']['fuel_lhv_kwh_per_nm3'],
        dt_hours=common['dt_hours'],intervals=len(load))
    results={}
    for route in ('R0','R1','R2','R3'):
        opts={'common':common}
        if route!='R0':
            opts['chp']=dict(chp_routes[route],availability=[1]*len(load),
                minimum_load_fraction=sizing['chp_minimum_load_fraction'])
        if route=='R2':
            # CHP minimum load must be passed once, through R2's biogas arguments.
            opts['chp'].pop('minimum_load_fraction')
            opts['biogas']=sizing['biogas']
        if route=='R3':opts['cgob']={'cgob_coverage_nm3':1.}
        m=build_architecture(route,**opts)
        solved=solve_highs(m)
        if not solved['optimal']:raise RuntimeError(f'{route}: {solved}')
        dt=common['dt_hours']
        grid_kwh=sum(p.value(m.grid[t]) for t in m.T)*dt
        result={'optimal':True,'grid_kwh':grid_kwh,
                'peak_pcc_kw':max(p.value(m.grid[t]) for t in m.T)}
        if route!='R0':
            result['chp_fuel_nm3']=sum(p.value(m.chp.fuel_nm3[t]) for t in m.T)
            result['chp_gross_kwh']=sum(p.value(m.chp.power_gross_kw[t]) for t in m.T)*dt
        if route=='R2':
            result['auxiliary_kwh']=sum(p.value(m.auxiliary_load_kw[t]) for t in m.T)*dt
            result['gas_initial_nm3']=p.value(m.gas_stock[0])
            result['gas_terminal_nm3']=p.value(m.gas_stock[len(load)])
            result['gas_curtailed_nm3']=sum(p.value(m.gas_curtailment[t]) for t in m.T)
            result['gas_physical_leakage_nm3']='NOT_MODELLED_NO_NUMERIC_CLAIM'
            result['gas_balance_residual_nm3']=result['gas_terminal_nm3']-result['gas_initial_nm3']-(
                sum(sizing['biogas']['production_nm3'])-result['chp_fuel_nm3']-result['gas_curtailed_nm3'])
            result['auxiliary_fraction_residual_kwh']=result['auxiliary_kwh']-sizing['biogas']['auxiliary_fraction_chp_gross']*result['chp_gross_kwh']
            if abs(result['gas_balance_residual_nm3'])>1e-5 or abs(result['auxiliary_fraction_residual_kwh'])>1e-5:
                raise RuntimeError('R2: falha de conservação de massa/energia')
        results[route]=result
    report={'gate':'REV052_PHYSICAL_CONDITIONAL','scientific_validation':False,
            'annualization':'BLOCKED','nsga2':'BLOCKED','f1_f3':'NOT_CALCULATED',
            'source_day':{'scenario':'E100','index':0,'intervals':len(load),'solar_status':solar_status},
            'parameterization':params['audit'],'r2_sizing':sizing,'results':results,
            'rev09_boundary_evidence':boundary,
            'remaining_limits':['substrate_t_per_day is a conditional assumption',
                'no endogenous digester optimization','constant biogas composition and production',
                'no physical gas leakage model; curtailment is operational discard','CHP availability all 96 intervals is synthetic',
                'R3 CGOB is attribute only','no annual validation']}
    dest=ROOT/'reports/D28_REV052_FISICA_CONDICIONADA.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(results,indent=2,ensure_ascii=False))
    print('CONDICIONADO; SEM F1/F3; SEM ANUALIZAÇÃO; NSGA-II BLOQUEADO')
    print('Relatório:',dest)
if __name__=='__main__':run()
