"""REV03: conecta solução anual R0 real a parcelas F1/F3, sem anualização fictícia.

Lê os arquivos já produzidos pelo solver e pela REV01/REV02. Não executa MILP.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / 'results/r0_annual_validation/annual_A_E100.json'
PREFLIGHT = ROOT / 'reports/D28_PILOTO_OPERACIONAL_ANUAL_R0.json'
REV01 = ROOT / 'reports/D28_CONTRATOS_ANUAIS_F1_F3_INTEGRADOS_REV01.json'
REV02 = ROOT / 'reports/D28_PARCELAS_F1_F3_CALCULAVEIS_REV02.json'
OUT = ROOT / 'reports/D28_DESPACHO_ANUAL_F1_F3_INTEGRADO_REV03.json'


def read_verified(path):
    raw = path.read_bytes()
    return json.loads(raw), {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest()}


def positive_finite(value, label, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: valor não numérico ou não finito')
    if value < 0 or (not allow_zero and value == 0):
        raise ValueError(f'{label}: valor inválido')
    return float(value)


def integrate(solver, preflight, annual, components, sources):
    if solver.get('status') != 'OPTIMAL' or solver.get('termination') != 'optimal':
        raise ValueError('Resultado do solver não certificado como ótimo')
    if solver.get('experiment') != 'R0_ANNUAL_A_E100' or solver.get('scenario') != 'E100':
        raise ValueError('Identidade do experimento anual não corresponde a R0/A/E100')
    if preflight.get('status') != 'ANNUAL_R0_CONDITIONAL_OPTIMAL' or preflight.get('design') != 'A' or preflight.get('scenario') != 'E100':
        raise ValueError('Relatório de execução anual não corresponde a R0/A/E100')
    if preflight.get('solver_process_returncode') != 0 or preflight.get('solver_status') != 'OPTIMAL':
        raise ValueError('Processo do solver sem conclusão válida')
    if preflight.get('solver_result_path', '').replace('\\', '/') != 'results/r0_annual_validation/annual_A_E100.json':
        raise ValueError('Caminho do resultado divergente')
    if solver.get('intervals') != 35040 or preflight.get('intervals') != 35040 or abs(solver.get('dt_hours', 0) - .25) > 1e-12:
        raise ValueError('Horizonte cronológico incompatível')
    grid = positive_finite(solver.get('grid_energy_kwh'), 'grid_energy_kwh')
    peak = positive_finite(solver.get('grid_peak_kw'), 'grid_peak_kw', True)
    pcc = positive_finite(solver.get('pcc_kw'), 'pcc_kw')
    charging = positive_finite(preflight.get('annual_charging_ac_kwh'), 'annual_charging_ac_kwh')
    if not math.isclose(grid, preflight.get('annual_grid_energy_kwh', -1), rel_tol=1e-9, abs_tol=1e-5):
        raise ValueError('Energia de rede divergente entre solver e relatório')
    if not math.isclose(peak, preflight.get('annual_grid_peak_kw', -1), rel_tol=1e-9, abs_tol=1e-5):
        raise ValueError('Pico de rede divergente entre solver e relatório')
    if peak > pcc + 1e-6 or abs(solver.get('soc_closure_residual_kwh', 1)) > 1e-6:
        raise ValueError('Violação de PCC ou SOC cíclico')
    if components.get('annualized_R0_R3') is not False:
        raise ValueError('REV02 não é uma execução anual otimizada')
    registry = annual['parameter_registry']
    factor = registry['D11-017']
    numeric = factor.get('numeric_value')
    if numeric is None:
        numeric = factor.get('raw_value')
    if numeric is None:
        raise ValueError('D11-017 sem fator quantitativo')
    emission_factor = positive_finite(float(numeric), 'D11-017', True)
    if not math.isclose(emission_factor, 0.0996, rel_tol=1e-9):
        # Não substitui o valor por 0.0996; apenas impede erro de fonte/escala silencioso.
        raise ValueError('D11-017 divergente do fator de referência REV02; revisar unidade e origem')
    emissions = grid * emission_factor
    out = {
        'revision': 'REV03_INTEGRACAO_DESPACHO_ANUAL',
        'case': 'R0_A_E100',
        'classification': 'OPTIMAL_MILP_CONDITIONAL_SYNTHETIC_COUNTERFACTUAL',
        'source_files': sources,
        'model_scope': {'intervals': 35040, 'dt_hours': .25, 'objective': solver.get('objective'),
                        'evidence': preflight.get('evidence'), 'caveats': preflight.get('caveats')},
        'physical_dispatch': {
            'grid_import_kwh_year': grid, 'grid_peak_kw': peak, 'pcc_limit_kw': pcc,
            'charging_ac_kwh_year': charging, 'charging_peak_ac_kw': preflight.get('charging_peak_ac_kw'),
            'pv_capacity_kw': solver.get('pv_capacity_kw'),
            'bess_capacity_kwh': solver.get('bess_capacity_kwh'),
            'pcs_power_kw': solver.get('pcs_power_kw'),
            'soc_closure_residual_kwh': solver.get('soc_closure_residual_kwh'),
            'energy_difference_charging_minus_grid_kwh': charging-grid,
            'energy_difference_is_not_pv_generation': True,
            'pv_generation_kwh_year': None, 'bess_charge_kwh_year': None,
            'bess_discharge_kwh_year': None, 'bess_losses_kwh_year': None,
        },
        'F1_components': {
            'annual_grid_import_kwh': grid,
            'annual_energy_purchase_cost_brl': None,
            'annual_demand_charge_brl': None,
            'annual_operating_cost_brl': None,
            'investment_and_replacement_costs_brl': None,
            'approved_annual_pkm': None,
            'F1_final': None,
            'pending': ['tariff_period_and_demand_contract_mapping', 'CAPEX_OPEX_replacements',
                        'approved_annual_PKM', '20_year_scenario_dispatch_and_cashflows'],
        },
        'F3_components': {
            'annual_grid_import_kwh': grid,
            'grid_emission_factor_kgco2e_per_kwh': emission_factor,
            'factor_parameter_id': 'D11-017',
            'factor_source': {k: factor.get(k) for k in ('unit', 'source_file', 'evidence_status', 'numeric_is_approved')},
            'conditional_grid_operational_emissions_kgco2e_year': emissions,
            'conditional_grid_operational_emissions_tco2e_year': emissions/1000,
            'annual_other_operational_emissions_kgco2e': None,
            'embodied_lifecycle_emissions_kgco2e': None,
            'approved_annual_pkm': None,
            'F3_final': None,
            'pending': ['D11-017_applicability_and_approval', 'other_operational_fuels',
                        'nonoverlapping_embodied_LCA', 'approved_annual_PKM', '20_year_scenario_dispatch'],
        },
        'F1': None, 'F3': None,
        'interpretation': 'Emissões condicionais = importação anual otimizada R0/A/E100 x D11-017. Não usar a energia sintética bruta de recarga como importação; não atribuir este ano a 20 anos; não calcular F1/F3 finais.',
    }
    return out


def main():
    paths = [SOLVER, PREFLIGHT, REV01, REV02]
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.is_file()]
    if missing:
        raise SystemExit('Arquivos necessários ausentes: ' + ', '.join(missing))
    read = [read_verified(p) for p in paths]
    result = integrate(*(x[0] for x in read), [x[1] for x in read])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Caso:', result['case'], '| estado:', result['classification'])
    print('Rede anual (kWh):', result['physical_dispatch']['grid_import_kwh_year'])
    print('Emissões operacionais condicionais (tCO2e):', result['F3_components']['conditional_grid_operational_emissions_tco2e_year'])
    print('F1/F3 finais:', result['F1'], result['F3'])
    print('Relatório:', OUT)


if __name__ == '__main__':
    main()
