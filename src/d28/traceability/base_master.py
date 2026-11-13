"""Read-only, fail-closed traceability for D28 Base Mestre. No parameter approval implied."""
from __future__ import annotations
import hashlib
import json
import math
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
# Explicit bindings; no fuzzy name matching and no implicit unit conversions.
BINDINGS = {
 'D02-002': ('design.pv_capacity_max_kwp','kWp'),
 'D04-007': ('transport.mean_occupancy_passengers_per_bus','passageiros/ônibus'),
 'D05-001': ('dispatch.pcc_import_limit_kw','kW'),
 'D05-003': ('economics.energy_tariff_brl_per_kwh','R$/kWh'),
 'D05-004': ('economics.demand_tariff_brl_per_kw_month','R$/kW.mês'),
 'D06-006': ('economics.pv_capex_brl_per_kwp','R$/kWp'),
 'D06-007': ('economics.pv_fixed_opex_fraction_of_pv_capex_year','fração CAPEX/ano'),
 'D07-003': ('economics.bess_max_c_rate_per_hour','1/h'),
 'D07-013': ('economics.bess_capex_brl_per_kwh','R$/kWh'),
 'D07-014': ('economics.pcs_capex_brl_per_kw','R$/kW'),
 'D07-015': ('economics.bess_fixed_opex_fraction_of_bess_capex_year','fração CAPEX/ano'),
 'D08-001': ('dispatch.r2.fuel_lhv_kwh_per_nm3','kWh/Nm³'),
 'D08-008': ('economics.r2.digester_capex_brl_per_t_year','R$/(t/ano)'),
 'D08-011': ('economics.r2.substrate_brl_per_t','R$/t'),
 'D09-002': ('dispatch.chp.electrical_efficiency','fração'),
 'D09-004': ('dispatch.chp.availability','fração anual'),
 'D09-005': ('dispatch.r1_r3.fuel_lhv_kwh_per_nm3','kWh/Nm³'),
 'D09-006': ('economics.r2.chp_capex_brl_per_kwe','R$/kWe'),
 'D09-007': ('economics.r1_r3.chp_capex_brl_per_kwe','R$/kWe'),
 'D09-010': ('economics.r1_r3.gas_price_brl_per_nm3','R$/Nm³'),
 'D09-014': ('economics.r3.cgob_premium_brl_per_nm3','R$/Nm³ equivalente'),
 'D10-002': ('economics.horizon_years','anos'),
 'D10-003': ('economics.discount_rate_real_year','fração/ano'),
 'D10-004': ('economics.engineering_contingency_fraction','fração CAPEX direto'),
 'D11-013': ('lca.bess_initial_kgco2e_per_kwh','kgCO2e/kWh de capacidade instalada'),
 'D11-017': ('lca.sin_lifecycle_kgco2e_per_kwh','kgCO2e/kWh gerado (SIN histórico)'),
 'D13-001': ('dispatch.dt_minutes','min'),
 'D13-004': ('objectives.F1.definition','R$/PKM'),
 'D13-005': ('objectives.F2.definition','kW'),
 'D13-006': ('objectives.F3.definition','kgCO2e/PKM'),
}
MISSING_LCA = ('D11-014','D11-015','D11-016','D11-018','D11-019')


def _cells(sheet_xml: bytes, strings: list[str]):
    root = ET.fromstring(sheet_xml)
    for row in root.findall('.//m:sheetData/m:row', NS):
        result = {}
        for cell in row.findall('m:c', NS):
            col = re.match(r'[A-Z]+', cell.attrib['r']).group()
            v = cell.find('m:v', NS)
            inline = cell.find('m:is', NS)
            raw = v.text if v is not None else (''.join(inline.itertext()) if inline is not None else None)
            if cell.attrib.get('t') == 's' and raw is not None:
                raw = strings[int(raw)]
            result[col] = raw
        yield result


def load_base_master(path: str | Path):
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rows = list(_cells(z.read('xl/worksheets/sheet1.xml'), strings))
    if not rows or rows[0].get('A') != 'ID' or rows[0].get('D') != 'Valor REV20' or rows[0].get('W') is None:
        raise ValueError('Layout da Base Mestre inesperado: interrompida a vinculação')
    records = []
    for row in rows[1:]:
        id_ = row.get('A')
        if not id_:
            continue
        if not re.fullmatch(r'D\d\d-\d\d\d', id_):
            raise ValueError(f'ID inválido: {id_}')
        symbol, expected_unit = BINDINGS.get(id_, (None, None))
        unit = row.get('E') or None
        records.append({'id':id_, 'group':row.get('B'), 'name':row.get('C'),
          'value_raw':row.get('D'), 'unit':unit, 'source_reference':row.get('F'),
          'source_url':row.get('G'), 'evidence_status':row.get('W'),
          'source_audit_status':row.get('Q'), 'model_symbol':symbol,
          'expected_unit':expected_unit,
          'unit_exact_match':(unit == expected_unit) if symbol else None,
          'usage':'MAPPED_CONDITIONAL_NOT_APPROVED' if symbol else 'NOT_MAPPED',
          'missing_lca_factor':id_ in MISSING_LCA})
    ids = [r['id'] for r in records]
    if len(ids) != len(set(ids)) or len(records) != 137:
        raise ValueError(f'Base Mestre inválida: {len(records)} registros, {len(set(ids))} IDs únicos (esperados 137)')
    return records


def controlled_values(records, *, approved_ids=()):
    """Export ONLY explicitly researcher-approved IDs; never imply approval from workbook status.

    Even approved IDs require exact unit matching and a finite numeric value.
    """
    by_id = {r['id']:r for r in records}
    out = {}
    for id_ in approved_ids:
        if id_ not in by_id:
            raise ValueError(f'ID não encontrado: {id_}')
        r = by_id[id_]
        if not r['model_symbol'] or not r['unit_exact_match']:
            raise ValueError(f'{id_}: vínculo/unidade não validado')
        try:
            val = float(r['value_raw'])
        except (ValueError, TypeError):
            raise ValueError(f'{id_}: valor não numérico') from None
        if not math.isfinite(val):
            raise ValueError(f'{id_}: valor não finito')
        out[r['model_symbol']] = {'value':val,'unit':r['unit'],'base_master_id':id_,
           'source_reference':r['source_reference'],'researcher_approved_for_this_run':True}
    return out


def build_report(path):
    path = Path(path)
    records = load_base_master(path)
    return {'scope':'PARAMETER_TRACEABILITY_ONLY_NO_MILP_RUN',
      'source_file':path.name, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
      'record_count':len(records),'mapped_count':sum(bool(r['model_symbol']) for r in records),
      'mapped_exact_unit_count':sum(r['unit_exact_match'] is True for r in records),
      'approved_for_execution_count':0,'annual_contract':'PENDING',
      'nsga2':'BLOCKED','records':records}
