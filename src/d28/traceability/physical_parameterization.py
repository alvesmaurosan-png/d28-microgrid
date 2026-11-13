"""REV05.1: cobertura física condicionada, sem homologação ou anualização."""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
from d28.traceability.base_master import load_base_master
from d28.traceability.controlled_injection import inject_conditional

# Vinculação explícita e somente para parâmetros aceitos pelo construtor atual.
PHYSICAL_BINDINGS = {
    'D02-002': ('common', 'pv_capacity_max_kwp', 'kWp'),
    'D07-003': ('constraint', 'bess_max_c_rate_per_hour', '1/h'),
    'D07-004': ('constraint', 'soc_min', 'fração'),
    'D07-005': ('constraint', 'soc_max', 'fração'),
    'D07-006': ('common', 'initial_soc', 'fração'),
    'D07-007': ('constraint', 'eta_round_trip', 'fração'),
    'D07-008': ('common', 'eta_charge', 'fração'),
    'D07-009': ('common', 'eta_discharge', 'fração'),
    'D07-010': ('common', 'soh', 'fração'),
    'D09-003': ('constraint', 'chp_minimum_load_fraction', 'fração Pnom'),
}
# Estes requisitos NÃO são cobertos pela interface física existente.
UNRESOLVED = {
    'D08-002': 'fração de metano: biodigestão ainda sem balanço de composição',
    'D08-003': 'rendimento de metano: produção exógena, não dimensionamento endógeno',
    'D08-005': 'TRH: biodigestor não dimensionado no MILP',
    'D08-006': 'fração útil: biodigestor não dimensionado no MILP',
    'D08-007': 'densidade: biodigestor não dimensionado no MILP',
    'D08-013': 'auxiliares de biodigestão: dependência da potência CHP não implementada',
    'D09-004': 'disponibilidade anual não pode virar série binária de 96 intervalos sem calendário',
    'D09-011': 'autonomia do gasômetro exige vazão de projeto e regra de dimensionamento',
}

def _finite(rec, *, lo=None, hi=None):
    try:
        value = float(rec['value_raw'])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{rec['id']}: valor não numérico") from exc
    if not math.isfinite(value) or (lo is not None and value < lo) or (hi is not None and value > hi):
        raise ValueError(f"{rec['id']}: valor fora do domínio")
    return value

def parameterize_physical(base_path, *, common, chp, selected_ids=None, purpose='DIAGNOSTIC_SOURCE_DAY'):
    if purpose != 'DIAGNOSTIC_SOURCE_DAY':
        raise ValueError('Somente dia-fonte diagnóstico')
    records = {r['id']: r for r in load_base_master(base_path)}
    supported = set(PHYSICAL_BINDINGS) | {'D05-001','D13-001','D09-002','D09-005','D08-001'}
    ids = tuple(sorted(supported) if selected_ids is None else selected_ids)
    if len(ids) != len(set(ids)) or not set(ids) <= supported:
        raise ValueError('Seleção contém duplicação ou parâmetro sem suporte físico')
    original = tuple(i for i in ids if i not in PHYSICAL_BINDINGS)
    baseline = inject_conditional(base_path, selected_ids=original, common=common, chp=chp)
    cfg = dict(baseline['common'])
    chp_routes = baseline['chp_by_route']
    checks = {}
    audits = list(baseline['audit']['injections'])
    for id_ in ids:
        if id_ not in PHYSICAL_BINDINGS:
            continue
        scope, key, unit = PHYSICAL_BINDINGS[id_]
        rec = records[id_]
        if rec['unit'] != unit:
            raise ValueError(f'{id_}: unidade não corresponde à vinculação física')
        value = _finite(rec, lo=0)
        if id_ in ('D07-004','D07-005','D07-006','D07-007','D07-008','D07-009','D07-010','D09-003') and not 0 < value <= 1:
            raise ValueError(f'{id_}: fração fora de (0,1]')
        before = cfg.get(key) if scope == 'common' else None
        if scope == 'common':
            cfg[key] = value
        else:
            checks[key] = value
        audits.append({'id':id_, 'model_symbol':key, 'destinations':[f'{scope}.{key}'],
                       'value_original':value,'value_injected':value,'unit_original':unit,
                       'previous_diagnostic_value':before,
                       'source_reference':rec['source_reference'], 'evidence_status':rec['evidence_status'],
                       'approval':'NOT_HOMOLOGATED_DIAGNOSTIC_ONLY',
                       'application':'CONSTRUCTOR_INPUT' if scope=='common' else 'CONSISTENCY_CHECK_ONLY'})
    # Evitar que o teste de consistência seja interpretado como parametrização do modelo.
    if 'soc_min' in checks and 'soc_max' in checks and checks['soc_min'] >= checks['soc_max']:
        raise ValueError('SOC mínimo >= máximo')
    if 'initial_soc' in cfg:
        if not checks.get('soc_min', .1) <= cfg['initial_soc'] <= checks.get('soc_max', .9):
            raise ValueError('SOC inicial fora dos limites')
    if 'eta_round_trip' in checks and 'eta_charge' in cfg and 'eta_discharge' in cfg:
        # Valores da Base Mestre são arredondados (0,922² ~= 0,850084).
        if abs(cfg['eta_charge'] * cfg['eta_discharge'] - checks['eta_round_trip']) > .001:
            raise ValueError('Eficiência round-trip incompatível')
    if 'bess_max_c_rate_per_hour' in checks:
        bess, pcs = cfg.get('bess_capacity_kwh'), cfg.get('pcs_power_kw')
        if bess is not None and pcs is not None and float(pcs) > checks['bess_max_c_rate_per_hour'] * float(bess) + 1e-9:
            raise ValueError('PCS excede C-rate da Base Mestre')
        if abs(checks['bess_max_c_rate_per_hour'] - .55) > 1e-9:
            raise ValueError('C-rate da Base difere do limite fixo no construtor; alterar equação antes de executar')
    if 'soc_min' in checks and abs(checks['soc_min'] - .1) > 1e-9:
        raise ValueError('SOC mínimo difere do limite fixo no construtor')
    if 'soc_max' in checks and abs(checks['soc_max'] - .9) > 1e-9:
        raise ValueError('SOC máximo difere do limite fixo no construtor')
    if 'chp_minimum_load_fraction' in checks and abs(checks['chp_minimum_load_fraction'] - .5) > 1e-9:
        raise ValueError('Carga mínima CHP difere do limite fixo no construtor')
    if cfg.get('pv_capacity_max_kwp') is not None and cfg.get('pv_capacity_kw') is not None:
        if cfg['pv_capacity_kw'] > cfg['pv_capacity_max_kwp']:
            raise ValueError('FV instalado excede teto geométrico')
    return {'common':cfg, 'chp_by_route':chp_routes, 'checks':checks,
            'audit':{'selected_ids':list(ids),'injections':audits,
                     'unresolved_physical_parameters':UNRESOLVED,
                     'base_master_sha256':hashlib.sha256(Path(base_path).read_bytes()).hexdigest(),
                     'scientific_approval':False,'annualization':'BLOCKED','nsga2':'BLOCKED',
                     'gate':'PHYSICAL_PARAMETERIZATION_CONDITIONAL'}}
