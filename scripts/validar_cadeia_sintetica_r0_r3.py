"""Executar da raiz: python scripts/validar_cadeia_sintetica_r0_r3.py"""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from d28.optimization.synthetic_chain_r0_r3 import SyntheticInputs, evaluate_synthetic

COMMON = dict(load_kw=[100.,150.,120.,80.], pv_pu=[0.,.3,.5,.1],
              pv_capacity_kw=100., bess_capacity_kwh=100., pcs_power_kw=40.,
              pcc_cap_kw=2500., dt_hours=.25, terminal_policy='cyclic')
CHP = dict(chp_capacity_kw=60., electrical_efficiency=.30,
           fuel_lhv_kwh_per_nm3=6., availability=[1,1,1,1])
# Valores redondos e arbitrários, EXCLUSIVAMENTE para teste de encadeamento.
ASSUMPTIONS = dict(pkm_horizon=1000., grid_brl_per_kwh=1.,
                   grid_kgco2e_per_kwh=.1, fuel_brl_per_nm3=2.,
                   fuel_kgco2e_per_nm3=.2, equipment_cost_brl_horizon=10.,
                   equipment_kgco2e_horizon=1.)

def run():
    result = {}
    for route in ('R0','R1','R2','R3'):
        kw = dict(common=COMMON, inputs=SyntheticInputs(**ASSUMPTIONS))
        if route != 'R0': kw['chp'] = CHP
        if route == 'R2':
            kw['biogas'] = dict(production_nm3=[5.]*4,
                               gasometer_capacity_nm3=50., initial_gas_nm3=20.)
        if route == 'R3': kw['cgob'] = dict(cgob_coverage_nm3=1.)
        result[route] = evaluate_synthetic(route, **kw)
    output = ROOT/'reports'/'REV05_CADEIA_SINTETICA_R0_R3.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v['objectives'] for k,v in result.items()},indent=2))
    print('ESCOPO: SINTÉTICO, NÃO ANUAL; NSGA-II BLOQUEADO')
    print('Relatório:',output)

if __name__ == '__main__': run()
