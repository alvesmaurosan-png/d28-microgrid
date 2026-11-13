"""Dia-fonte REV09/REV12 com parâmetros legados explicitamente rastreados.

F1/F3 seguem DIAGNÓSTICOS SINTÉTICOS; não são resultados científicos.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from d28.traceability.controlled_injection import inject_conditional
from d28.optimization.synthetic_chain_r0_r3 import SyntheticInputs, evaluate_synthetic
from validar_d28_dia_fonte_r0_r3 import (source_day, COMMON_DESIGN, CHP_DESIGN,
    COEFFICIENTS, PKM_DIAGNOSTIC, DEMAND, SOLAR, CONTRACT)

BASE = ROOT / 'data/raw/parameters/Base_Mestre_D28_PC_REV07_REV02.xlsx'
# Seleção para ESTA execução experimental; não implica homologação dos valores.
SELECTED_IDS = ('D05-001', 'D13-001', 'D09-002', 'D09-005', 'D08-001')

def run():
    contract = json.loads(CONTRACT.read_text(encoding='utf-8-sig'))
    if contract.get('status') == 'APPROVED':
        raise RuntimeError('Script exclusivo de cenário condicionado; contrato anual aprovado exige fluxo próprio')
    load, pv, solar_status = source_day('E100', 0)
    injected = inject_conditional(BASE, selected_ids=SELECTED_IDS,
                                  common=COMMON_DESIGN, chp=CHP_DESIGN)
    common = dict(injected['common'], load_kw=load, pv_pu=pv)
    assumptions = SyntheticInputs(pkm_horizon=PKM_DIAGNOSTIC, **COEFFICIENTS)
    results = {}
    for route in ('R0', 'R1', 'R2', 'R3'):
        kwargs = {'common': common, 'inputs': assumptions}
        if route != 'R0':
            kwargs['chp'] = dict(injected['chp_by_route'][route], availability=[1] * len(load))
        if route == 'R2':
            kwargs['biogas'] = {'production_nm3': [5.] * len(load),
                               'gasometer_capacity_nm3': 500., 'initial_gas_nm3': 250.}
        if route == 'R3':
            kwargs['cgob'] = {'cgob_coverage_nm3': 1.}
        results[route] = evaluate_synthetic(route, **kwargs)
        if not results[route]['audit']['solver']['optimal']:
            raise RuntimeError(f'{route}: despacho não ótimo')
    report = {'gate': 'D28_CONDITIONAL_BASE_MASTER_INJECTION_SOURCE_DAY',
              'scientific_objectives_validated': False, 'annualization': 'BLOCKED',
              'nsga2': 'BLOCKED', 'scenario': 'E100', 'day_index': 0,
              'intervals': len(load), 'solar_status': solar_status,
              'demand_semantics': 'REV09_AC_AGGREGATE_NO_AUXILIARY_ADDITION',
              'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (DEMAND, SOLAR, CONTRACT)},
              'parameter_injection': injected['audit'],
              'remaining_diagnostic_assumptions': {
                  'common_design': {k:v for k,v in common.items() if k not in ('load_kw','pv_pu')},
                  'chp_by_route': injected['chp_by_route'],
                  'R2_production_nm3_per_interval': 5., 'R2_gasometer_capacity_nm3': 500.,
                  'R2_initial_gas_nm3': 250., 'R3_cgob_coverage_nm3': 1.,
                  'pkm_diagnostic': PKM_DIAGNOSTIC, 'coefficients': COEFFICIENTS},
              'results': results}
    out = ROOT / 'reports/D28_REV05_INJECAO_CONDICIONADA_DIA_FONTE.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({r: {'optimal':v['audit']['solver']['optimal'],
                           'grid_kwh':v['audit']['grid_kwh'],
                           'F2_kW':v['objectives']['F2_kW'],
                           'F1_DIAGNOSTIC':v['objectives']['F1_BRL_per_pkm'],
                           'F3_DIAGNOSTIC':v['objectives']['F3_kgCO2e_per_pkm']}
                      for r,v in results.items()}, ensure_ascii=False, indent=2))
    print('CONDICIONADO: VALORES LEGADOS NÃO HOMOLOGADOS; F1/F3 DIAGNÓSTICOS; NÃO ANUAL')
    print('Relatório:', out)

if __name__ == '__main__':
    run()
