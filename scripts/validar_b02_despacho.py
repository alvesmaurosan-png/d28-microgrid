"""B02: teste real, curto, do despacho econômico epsilon; não homologa F1 anual."""
import json
from pathlib import Path
from d28.optimization.biobjective_milp_connector import ConnectorInputs
from d28.optimization.economic_dispatch_f1f2 import EnergyPrices, solve_economic

def main():
    inp = ConnectorInputs(load_kw=(100., 150., 120., 80.), pv_pu=(0., 0., 0., 0.),
                          dt_hours=.25, pcc_cap_kw=250., terminal_policy='cyclic')
    design = {'pv_kw': 0., 'bess_kwh': 200., 'pcs_kw': 100.}
    prices = EnergyPrices(grid_brl_kwh=(1., 1., 1., 1.))
    runs = {}
    for name, epsilon in [('unrestricted', None), ('peak_cap_140', 140.)]:
        try:
            result = solve_economic('R0', design, inp, prices, epsilon_kw=epsilon)
            runs[name] = {k:v for k,v in result.items() if k!='grid_kw'}
            if 'grid_kw' in result: runs[name]['grid_kw'] = result['grid_kw']
        except Exception as exc:
            runs[name]={'status':'ERROR','exception':type(exc).__name__+': '+str(exc)}
    a,b = runs['unrestricted'],runs['peak_cap_140']
    valid = all(x.get('status')=='PASS' and all(x.get('checks',{}).values()) for x in (a,b))
    if valid:
        valid = (b['pilot_f2_kw'] <= 140.+1e-5 and
                 b['cost_brl']+1e-5 >= a['cost_brl'] and
                 abs(b['cost_brl']-sum(b['cost_components_brl'].values()))<=1e-5)
    report={'test':'B02_ECONOMIC_EPSILON_REAL_MILP','status':'PASS' if valid else 'FAILED',
            'scope':'FOUR_INTERVALS_R0_NOT_ANNUAL_NOT_HOMOLOGATION',
            'f1_annual_calculated':False,'demand_charge_in_dispatch_objective':False,
            'scientific_limitation':'Annual F1 includes monthly demand charges; minimizing variable energy cost alone does not generally minimize F1.',
            'runs':runs}
    path=Path('reports/D28_B02_DESPACHO_ECONOMICO.json');path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False));print('RELATORIO:',path)
    raise SystemExit(0 if valid else 2)
if __name__=='__main__': main()
