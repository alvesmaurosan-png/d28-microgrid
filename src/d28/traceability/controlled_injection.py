"""Injeção experimental, somente por IDs explicitamente selecionados; nunca homologa."""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
from d28.traceability.base_master import load_base_master

# Destinos efetivamente suportados pelos construtores e pelo gate de dia-fonte.
# D02-002 é LIMITE de projeto, não capacidade instalada; deliberadamente não injetado.
DESTINATIONS = {
    'D05-001': ('common', 'pcc_cap_kw', 'dispatch.pcc_import_limit_kw'),
    'D13-001': ('common', 'dt_hours', 'dispatch.dt_minutes'),
    'D09-002': ('chp', 'electrical_efficiency', 'dispatch.chp.electrical_efficiency'),
    'D09-005': ('chp_r1_r3', 'fuel_lhv_kwh_per_nm3', 'dispatch.r1_r3.fuel_lhv_kwh_per_nm3'),
    'D08-001': ('chp_r2', 'fuel_lhv_kwh_per_nm3', 'dispatch.r2.fuel_lhv_kwh_per_nm3'),
}

def inject_conditional(base_path, *, selected_ids, common, chp, purpose='DIAGNOSTIC_SOURCE_DAY'):
    """Devolve novas configurações e trilha de auditoria, sem mutar argumentos.

    selected_ids: seleção explícita para UMA execução diagnóstica; NÃO é aprovação.
    Falha fechada para IDs não suportados, duplicados, valores e unidades inválidos.
    """
    if purpose != 'DIAGNOSTIC_SOURCE_DAY':
        raise ValueError('Somente execução diagnóstica de dia-fonte é permitida')
    selected = tuple(selected_ids)
    if len(set(selected)) != len(selected):
        raise ValueError('IDs repetidos')
    records = {r['id']: r for r in load_base_master(base_path)}
    out_common = dict(common)
    out_chp = {route: dict(chp) for route in ('R1', 'R2', 'R3')}
    audit = []
    for id_ in selected:
        if id_ not in DESTINATIONS:
            raise ValueError(f'{id_}: injeção não suportada; nenhuma homologação implícita')
        rec = records[id_]
        target, key, symbol = DESTINATIONS[id_]
        if rec['model_symbol'] != symbol or not rec['unit_exact_match']:
            raise ValueError(f'{id_}: vínculo semântico/unidade incompatível')
        try:
            raw = float(rec['value_raw'])
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{id_}: valor não numérico') from exc
        if not math.isfinite(raw) or raw <= 0:
            raise ValueError(f'{id_}: valor inválido')
        value = raw / 60.0 if id_ == 'D13-001' else raw
        if id_ == 'D09-002' and not 0 < value <= 1:
            raise ValueError('Eficiência CHP fora de (0,1]')
        if target == 'common':
            before = out_common.get(key)
            out_common[key] = value
            destinations = [f'common.{key}']
        else:
            routes = ('R1', 'R2', 'R3') if target == 'chp' else (('R2',) if target == 'chp_r2' else ('R1', 'R3'))
            before = {route: out_chp[route].get(key) for route in routes}
            for route in routes:
                out_chp[route][key] = value
            destinations = [f'{route}.chp.{key}' for route in routes]
        audit.append({'id': id_, 'model_symbol': symbol, 'destinations': destinations,
                      'value_original': raw, 'unit_original': rec['unit'],
                      'value_injected': value, 'unit_injected': 'h' if id_ == 'D13-001' else rec['unit'],
                      'previous_diagnostic_value': before,
                      'source_reference': rec['source_reference'],
                      'evidence_status': rec['evidence_status'],
                      'approval': 'NOT_HOMOLOGATED_DIAGNOSTIC_ONLY'})
    return {'common': out_common, 'chp_by_route': out_chp,
            'audit': {'purpose': purpose, 'scientific_approval': False,
                      'annualization': 'BLOCKED', 'nsga2': 'BLOCKED',
                      'base_master_sha256': hashlib.sha256(Path(base_path).read_bytes()).hexdigest(),
                      'selected_ids': list(selected), 'injections': audit}}
