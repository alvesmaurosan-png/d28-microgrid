"""REV04: contabilização econômica exploratória de um despacho anual já resolvido.
Não executa solver, não pressupõe série horária nem homologa tarifas.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / 'results/r0_annual_validation/annual_A_E100.json'
REV03 = ROOT / 'reports/D28_DESPACHO_ANUAL_F1_F3_INTEGRADO_REV03.json'
CONFIG = ROOT / 'config/economics/r0_f1_exploratory_2026.json'
OUTPUT = ROOT / 'reports/D28_ECONOMIA_DESPACHO_ANUAL_REV04.json'


def load(path):
    raw = path.read_bytes()
    return json.loads(raw), {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest()}


def number(obj, key, *, positive=False):
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{key}: valor quantitativo ausente ou inválido')
    if value < 0 or (positive and value == 0):
        raise ValueError(f'{key}: valor negativo ou nulo')
    return float(value)


def integrate(solver, rev03, cfg, sources):
    if solver.get('status') != 'OPTIMAL' or solver.get('termination') != 'optimal' or solver.get('experiment') != 'R0_ANNUAL_A_E100':
        raise ValueError('Solução anual R0/A/E100 não certificada')
    if rev03.get('case') != 'R0_A_E100' or rev03.get('classification') != 'OPTIMAL_MILP_CONDITIONAL_SYNTHETIC_COUNTERFACTUAL':
        raise ValueError('REV03 incompatível')
    if cfg.get('status') != 'EXPLORATORY_NOT_HOMOLOGATED' or cfg.get('currency') != 'BRL_2026_real':
        raise ValueError('Configuração econômica não corresponde ao cenário exploratório esperado')
    physical = rev03['physical_dispatch']
    energy = number(solver, 'grid_energy_kwh', positive=True)
    peak = number(solver, 'grid_peak_kw', positive=True)
    if not math.isclose(energy, number(physical, 'grid_import_kwh_year'), rel_tol=1e-10, abs_tol=1e-4):
        raise ValueError('Energia divergente da REV03')
    if not math.isclose(peak, number(physical, 'grid_peak_kw'), rel_tol=1e-10, abs_tol=1e-5):
        raise ValueError('Pico divergente da REV03')
    pv = number(solver, 'pv_capacity_kw')
    bess = number(solver, 'bess_capacity_kwh')
    pcs = number(solver, 'pcs_power_kw')
    pv_cost = pv * number(cfg, 'pv_capex_brl_per_kwp')
    bess_cost = bess * number(cfg, 'bess_capex_brl_per_kwh')
    pcs_cost = pcs * number(cfg, 'pcs_capex_brl_per_kw')
    direct = pv_cost + bess_cost + pcs_cost
    contingency = direct * number(cfg, 'engineering_contingency_fraction')
    opex_pv = pv_cost * number(cfg, 'pv_fixed_opex_fraction_of_pv_capex_year')
    opex_bess = bess_cost * number(cfg, 'bess_fixed_opex_fraction_of_bess_capex_year')
    opex_pcs = pcs_cost * number(cfg, 'pcs_fixed_opex_fraction_of_pcs_capex_year')
    flat_cost = energy * number(cfg, 'energy_tariff_brl_per_kwh')
    demand_rate = number(cfg, 'demand_tariff_brl_per_kw_month')
    rate = number(cfg, 'discount_rate_real_year', positive=True)
    horizon = cfg.get('horizon_years')
    if type(horizon) is not int or horizon <= 0:
        raise ValueError('horizon_years inválido')
    replacements = []
    for prefix, base in [('pv_inverter', pv_cost), ('bess', bess_cost)]:
        year = cfg.get(prefix + '_replacement_year')
        if type(year) is not int or not 1 <= year <= horizon:
            raise ValueError('Ano de reposição inválido: ' + prefix)
        fraction = number(cfg, prefix + '_replacement_fraction_of_initial_' + ('pv_capex' if prefix == 'pv_inverter' else 'bess_capex'))
        nominal = base * fraction
        replacements.append({'component': prefix, 'year': year, 'conditional_cost_brl': nominal,
                             'discounted_cost_brl': nominal / (1 + rate) ** year})
    pv_factor = sum((1 + rate) ** (-t) for t in range(1, horizon + 1))
    emissions = number(rev03['F3_components'], 'conditional_grid_operational_emissions_tco2e_year')
    return {
        'revision': 'REV04_INTEGRACAO_ECONOMICA_DESPACHO_ANUAL', 'case': 'R0_A_E100',
        'status': 'CONDITIONAL_EXPLORATORY_NOT_HOMOLOGATED', 'sources': sources,
        'dispatch': {'grid_import_kwh_year': energy, 'grid_peak_kw': peak,
                     'pv_capacity_kw': pv, 'bess_capacity_kwh': bess, 'pcs_power_kw': pcs},
        'F1_components': {
            'energy_purchase_flat_tariff_exploratory_brl_year': flat_cost,
            'energy_purchase_flat_tariff_source_key': 'energy_tariff_brl_per_kwh',
            'time_of_use_energy_purchase_brl_year': None,
            'monthly_demand_charge_brl_year': None,
            'demand_overrun_charge_brl_year': None,
            'demand_tariff_reference_brl_per_kw_month': demand_rate,
            'demand_billing_note': 'Pico físico anual não é demanda faturável mensal; contrato, série mensal e regra de ultrapassagem ausentes',
            'pv_capex_brl': pv_cost, 'bess_capex_brl': bess_cost, 'pcs_capex_brl': pcs_cost,
            'direct_capex_brl': direct, 'engineering_contingency_brl': contingency,
            'conditional_initial_capex_brl': direct + contingency,
            'annual_fixed_opex_pv_brl': opex_pv, 'annual_fixed_opex_bess_brl': opex_bess,
            'annual_fixed_opex_pcs_brl': opex_pcs,
            'conditional_fixed_opex_brl_year': opex_pv + opex_bess + opex_pcs,
            'conditional_flat_energy_plus_fixed_opex_brl_year': flat_cost + opex_pv + opex_bess + opex_pcs,
            'conditional_replacements': replacements,
            'discount_factor_20y_or_configured_horizon': pv_factor,
            'discounted_illustrative_repeated_annual_flat_energy_and_fixed_opex_brl': (flat_cost + opex_pv + opex_bess + opex_pcs) * pv_factor,
            'illustrative_repeat_is_not_20y_dispatch': True,
            'approved_annual_pkm': None, 'F1_final': None,
        },
        'F3_components': {
            'conditional_grid_operational_emissions_tco2e_year': emissions,
            'factor_parameter_id': rev03['F3_components']['factor_parameter_id'],
            'other_operational_emissions_tco2e_year': None,
            'embodied_lifecycle_emissions_tco2e': None, 'F3_final': None,
        },
        'limitations': [
            'Tarifa plana é hipótese exploratória; não equivale à estrutura tarifária homologada',
            'Sem série de importação de 15 min, não há faturamento por posto tarifário nem demanda mensal',
            'Não há contrato de demanda, regra de ultrapassagem, tributos, bandeiras ou ajustes tarifários',
            'CAPEX e OPEX calculados com coeficientes exploratórios; não homologados',
            'Não se replica R0 E100 automaticamente por 20 anos para fechar F1',
            'F3 conserva a parcela de rede da REV03, sem inventário ACV completo',
        ],
        'F1': None, 'F3': None,
    }


def main():
    paths = [SOLVER, REV03, CONFIG]
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.is_file()]
    if missing:
        raise SystemExit('Arquivos ausentes: ' + ', '.join(missing))
    loaded = [load(p) for p in paths]
    report = integrate(*(x[0] for x in loaded), [x[1] for x in loaded])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Caso:', report['case'], '| estado:', report['status'])
    for k in ['energy_purchase_flat_tariff_exploratory_brl_year', 'conditional_initial_capex_brl', 'conditional_fixed_opex_brl_year']:
        print(k, '=', round(report['F1_components'][k], 2))
    print('Demanda faturável:', report['F1_components']['monthly_demand_charge_brl_year'])
    print('Emissões tCO2e:', report['F3_components']['conditional_grid_operational_emissions_tco2e_year'])
    print('F1/F3 finais:', report['F1'], report['F3'])
    print('Relatório:', OUTPUT)


if __name__ == '__main__':
    main()
