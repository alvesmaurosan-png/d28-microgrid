"""Executa o gate de dia-fonte R0–R3 com entradas físicas condicionadas."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from d28.traceability.physical_parameterization import parameterize_physical
from d28.optimization.synthetic_chain_r0_r3 import SyntheticInputs, evaluate_synthetic
from validar_d28_dia_fonte_r0_r3 import (source_day, COMMON_DESIGN, CHP_DESIGN,
    COEFFICIENTS, PKM_DIAGNOSTIC, DEMAND, SOLAR, CONTRACT)
BASE=ROOT/'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'

def run():
    contract=json.loads(CONTRACT.read_text(encoding='utf-8-sig'))
    if contract.get('status') == 'APPROVED':
        raise RuntimeError('Gate condicionado não admite contrato anual aprovado')
    load,pv,solar_status=source_day('E100',0)
    injection=parameterize_physical(BASE,common=COMMON_DESIGN,chp=CHP_DESIGN)
    common=dict(injection['common'],load_kw=load,pv_pu=pv)
    assumptions=SyntheticInputs(pkm_horizon=PKM_DIAGNOSTIC,**COEFFICIENTS)
    results={}
    for route in ('R0','R1','R2','R3'):
        kwargs={'common':common,'inputs':assumptions}
        if route != 'R0':
            kwargs['chp']=dict(injection['chp_by_route'][route],availability=[1]*len(load))
        if route=='R2':
            kwargs['biogas']={'production_nm3':[5.]*len(load),
                'gasometer_capacity_nm3':500.,'initial_gas_nm3':250.}
        if route=='R3':
            kwargs['cgob']={'cgob_coverage_nm3':1.}
        results[route]=evaluate_synthetic(route,**kwargs)
        if not results[route]['audit']['solver']['optimal']:
            raise RuntimeError(f'{route}: despacho não ótimo')
    report={'gate':'D28_REV051_CONDITIONAL_PHYSICAL_PARAMETERIZATION',
        'scientific_objectives_validated':False,'annualization':'BLOCKED','nsga2':'BLOCKED',
        'source_day':{'scenario':'E100','day_index':0,'intervals':len(load),
            'solar_status':solar_status,'demand_semantics':'REV09_AC_AGGREGATE_NO_DOUBLE_COUNT',
            'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (DEMAND,SOLAR,CONTRACT)}},
        'parameterization':injection['audit'],'physical_checks':injection['checks'],
        'remaining_experimental_assumptions':{
            'pv_bess_chp_design':{'common':{k:v for k,v in common.items() if k not in ('load_kw','pv_pu')},
                'chp_by_route':injection['chp_by_route']},
            'chp_availability':'ALL_96_INTERVALS_DIAGNOSTIC_NOT_D09_004',
            'r2_biogas_nm3_per_interval':5.,'r2_gasometer_nm3':500.,
            'r2_initial_gas_nm3':250.,'r3_cgob_nm3':1.,
            'f1_f3_coefficients':'SYNTHETIC_NOT_SCIENTIFIC'},'results':results}
    out=ROOT/'reports/D28_REV051_PARAMETRIZACAO_FISICA_CONDICIONADA.json'
    out.parent.mkdir(exist_ok=True,parents=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({r:{'optimal':v['audit']['solver']['optimal'],
        'grid_kwh':v['audit']['grid_kwh'],'F2_kW':v['objectives']['F2_kW']} for r,v in results.items()},indent=2))
    print('CONDICIONADO; F1/F3 SINTÉTICOS; SEM ANUALIZAÇÃO; NSGA-II BLOQUEADO')
    print('Relatório:',out)
if __name__=='__main__':run()
