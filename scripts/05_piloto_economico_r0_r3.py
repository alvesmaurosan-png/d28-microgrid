"""Execute na raiz do repositorio com .venv311 ativo."""
import json
from pathlib import Path
from d28.optimization.biobjective_milp_connector import ConnectorInputs
from d28.optimization.economic_dispatch_f1f2 import EnergyPrices, solve_economic
LOAD=(100.,150.,120.,80.); PV=(0.,.3,.5,.1)
DESIGN={'pv_kw':100.,'bess_kwh':500.,'pcs_kw':100.}
CHP={'chp_capacity_kw':80.,'electrical_efficiency':.35,'fuel_lhv_kwh_per_nm3':10.,'availability':(1,1,1,1)}
OPTIONS={'R0':{},'R1':dict(CHP),'R2':{**CHP,'production_nm3':(10.,)*4,'gasometer_capacity_nm3':200.,'initial_gas_nm3':100.,'auxiliary_kw':(2.,)*4,'terminal_gas_policy':'cyclic'},'R3':{**CHP,'cgob_coverage_nm3':0.}}
# PREÇOS EXCLUSIVAMENTE ILUSTRATIVOS; substituir por fontes homologadas.
PRICES={'R0':EnergyPrices((.5,.9,1.2,.6)),
        'R1':EnergyPrices((.5,.9,1.2,.6),fuel_brl_nm3=1.),
        'R2':EnergyPrices((.5,.9,1.2,.6),production_brl_nm3=.6,gas_loss_brl_nm3=.1),
        'R3':EnergyPrices((.5,.9,1.2,.6),fuel_brl_nm3=1.)}
results=[]
for route in OPTIONS:
    inp=ConnectorInputs(load_kw=LOAD,pv_pu=PV,dt_hours=.25,pcc_cap_kw=2500.,terminal_policy='cyclic',route_options=OPTIONS[route])
    try: result=solve_economic(route,DESIGN,inp,PRICES[route],epsilon_kw=120.)
    except Exception as exc: result={'route':route,'status':'ERROR','reason':f'{type(exc).__name__}: {exc}'}
    results.append(result)
    print(route,result['status'],result.get('cost_brl'),result.get('reason'))
report={'protocol':'D28_REV05_ECONOMIC_INTEGRATION_PILOT','synthetic_test_only':True,
        'prices_homologated':False,'annual_f1_calculated':False,'nsga2_executed':False,
        'f3_excluded':True,'results':results}
path=Path('results/rev05_piloto_economico_r0_r3.json');path.parent.mkdir(exist_ok=True,parents=True)
path.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
print('Auditoria:',path)
raise SystemExit(0 if all(r['status']=='PASS' for r in results) else 1)
