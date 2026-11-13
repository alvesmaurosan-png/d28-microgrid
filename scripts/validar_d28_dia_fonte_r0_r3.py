"""D28: primeiro dia-fonte REV09/REV12, despacho R0-R3, contabilidade diagnóstica.

F1/F3 usam coeficientes sintéticos do gate anterior; NÃO são indicadores científicos.
Sem anualização, sem adição de cargas auxiliares à demanda AC agregada REV09.
"""
from __future__ import annotations
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from d28.optimization.synthetic_chain_r0_r3 import SyntheticInputs, evaluate_synthetic

DEMAND = ROOT / 'data/raw/demanda/D28_REV09_demanda_15min.csv'
SOLAR = ROOT / 'data/raw/solar/D28_solar_15min_REV12_1_3.csv'
CONTRACT = ROOT / 'contrato_anual.json'

# Dimensionamentos e fatores SOMENTE de diagnóstico; NÃO homologados na Base Mestre.
# CHP e fatores são os mesmos do teste sintético anterior, estendidos a 96 intervalos.
COMMON_DESIGN = dict(pv_capacity_kw=100., bess_capacity_kwh=100., pcs_power_kw=40.,
                     pcc_cap_kw=2500., dt_hours=.25, terminal_policy='cyclic')
CHP_DESIGN = dict(chp_capacity_kw=60., electrical_efficiency=.30,
                  fuel_lhv_kwh_per_nm3=6.)
COEFFICIENTS = dict(grid_brl_per_kwh=1., grid_kgco2e_per_kwh=.1,
                    fuel_brl_per_nm3=2., fuel_kgco2e_per_nm3=.2,
                    equipment_cost_brl_horizon=10., equipment_kgco2e_horizon=1.)
PKM_DIAGNOSTIC = 1000.  # Apenas denominador artificial do teste de encadeamento.


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_day(scenario='E100', day_index=0):
    """Seleciona dia completo por chave de intervalo; recusa lacunas e duplicações."""
    with DEMAND.open(encoding='utf-8-sig', newline='') as f:
        demand = [r for r in csv.DictReader(f)
                  if r['scenario'] == scenario and int(r['day_index']) == day_index]
    with SOLAR.open(encoding='utf-8-sig', newline='') as f:
        solar = list(csv.DictReader(f))
    solar_by_start = {}
    for r in solar:
        key = int(r['interval_start_min'])
        if key in solar_by_start:
            raise ValueError('Intervalo solar duplicado')
        solar_by_start[key] = r
    if len(demand) != 96:
        raise ValueError(f'Dia REV09 incompleto: {len(demand)} intervalos')
    by_start = {}
    for r in demand:
        start, end = int(r['interval_start_min']), int(r['interval_end_min'])
        if start in by_start or end != start + 15:
            raise ValueError('REV09 com duplicação ou duração irregular')
        by_start[start] = r
    expected = set(range(day_index * 1440, (day_index + 1) * 1440, 15))
    if set(by_start) != expected:
        raise ValueError('REV09 sem cobertura completa do dia-fonte')
    load, pv, status = [], [], set()
    for start in sorted(expected):
        d = by_start[start]
        s = solar_by_start.get(start)
        if s is None or int(s['interval_end_min']) != start + 15:
            raise ValueError(f'REV12 sem correspondência temporal em {start}')
        load.append(float(d['power_ac_kw']))
        pv.append(float(s['pv_pu']))
        status.add(s.get('A701_status', 'NA'))
    if min(load + pv) < 0:
        raise ValueError('Série negativa')
    return load, pv, sorted(status)


def run():
    scenario, day_index = 'E100', 0
    load, pv, solar_status = source_day(scenario, day_index)
    contract = json.loads(CONTRACT.read_text(encoding='utf-8-sig'))
    if contract.get('status') == 'APPROVED':
        raise RuntimeError('Este gate é somente de dia-fonte; não usar contrato anual aprovado')
    common = dict(COMMON_DESIGN, load_kw=load, pv_pu=pv)
    assumptions = SyntheticInputs(pkm_horizon=PKM_DIAGNOSTIC, **COEFFICIENTS)
    results = {}
    for route in ('R0', 'R1', 'R2', 'R3'):
        kwargs = dict(common=common, inputs=assumptions)
        if route != 'R0':
            kwargs['chp'] = dict(CHP_DESIGN, availability=[1] * 96)
        if route == 'R2':
            kwargs['biogas'] = dict(production_nm3=[5.] * 96,
                                    gasometer_capacity_nm3=500., initial_gas_nm3=250.)
        if route == 'R3':
            kwargs['cgob'] = dict(cgob_coverage_nm3=1.)
        results[route] = evaluate_synthetic(route, **kwargs)
    report = dict(
        gate='D28_REAL_SERIES_SOURCE_DAY_DIAGNOSTIC',
        scientific_objectives_validated=False, nsga2_released=False,
        annualization='BLOCKED_BY_CONTRACT', contract_status=contract.get('status'),
        scenario=scenario, day_index=day_index, intervals=96, dt_hours=.25,
        demand_semantics='REV09_AC_AGGREGATE_NO_EXTRA_CHARGING_OR_AUXILIARY',
        solar_status=solar_status,
        provenance={'demand_path':str(DEMAND.relative_to(ROOT)), 'demand_sha256':sha256(DEMAND),
                    'solar_path':str(SOLAR.relative_to(ROOT)), 'solar_sha256':sha256(SOLAR),
                    'contract_sha256':sha256(CONTRACT)},
        observed_series_summary={'load_kwh':sum(load)*.25,'load_peak_kw':max(load),
                                 'pv_pu_sum':sum(pv)},
        diagnostic_assumptions={'common':COMMON_DESIGN,'chp':CHP_DESIGN,
                                'R2_production_nm3_per_interval':5.,
                                'R2_gasometer_nm3':500., 'R2_initial_gas_nm3':250.,
                                'R3_cgob_coverage_nm3':1.,
                                'synthetic_pkm_horizon':PKM_DIAGNOSTIC,
                                'synthetic_coefficients':COEFFICIENTS},
        results=results)
    out = ROOT / 'reports/D28_DIA_FONTE_REV09_REV12_R0_R3.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({r: {'optimal':v['audit']['solver']['optimal'],
                           'grid_kwh':v['audit']['grid_kwh'],
                           'F1_DIAGNOSTIC':v['objectives']['F1_BRL_per_pkm'],
                           'F2_kW':v['objectives']['F2_kW'],
                           'F3_DIAGNOSTIC':v['objectives']['F3_kgCO2e_per_pkm']}
                      for r,v in results.items()},ensure_ascii=False,indent=2))
    print('DADOS REV09/REV12: DIA-FONTE; F1/F3: COEFICIENTES SINTÉTICOS; NÃO ANUAL')
    print('Relatório:',out)

if __name__ == '__main__':
    run()
