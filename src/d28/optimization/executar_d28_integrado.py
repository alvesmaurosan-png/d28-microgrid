"""Ponto único de execução da cadeia integrada D28 (R0 comprovado).

Uso: python -m d28.optimization.executar_d28_integrado --config config/d28_exemplo_sintetico.json --output results/d28_integrado_sintetico
Os parâmetros econômicos deste exemplo são HIPÓTESES SINTÉTICAS, não D28 homologado.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from math import isfinite

from d28.economics.integrated_f1_rev02 import AnnualRecord, COST_KEYS
from d28.optimization.nsga2_scenario_bridge_rev02_3 import ScenarioContract, nsga2_evaluation_rev02_3
from d28.optimization.real_milp_providers_rev02_5 import (
    R0PhysicalInputs, TariffEvidence, make_r0_integrated_providers,
)


def _required_number(value, label, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or (value <= 0 if positive else value < 0):
        raise ValueError(f'{label}: exige número finito {"positivo" if positive else "não negativo"}')
    return float(value)


def load_contract(path):
    cfg = json.loads(Path(path).read_text(encoding='utf-8'))
    if cfg.get('execution_class') not in ('SYNTHETIC_DEMONSTRATION', 'CONDITIONAL_RESEARCH'):
        raise ValueError('execution_class obrigatório: SYNTHETIC_DEMONSTRATION ou CONDITIONAL_RESEARCH')
    if cfg.get('architecture') != 'R0':
        raise ValueError('Arquitetura não implementada por este executor: apenas R0')
    phys = cfg['physical']
    load, pv, months = phys['load_kw'], phys['pv_pu'], phys['months']
    if not load or len(load) != len(pv) or len(load) != len(months):
        raise ValueError('Séries físicas e calendário incompatíveis')
    for a in load: _required_number(a, 'load_kw')
    for a in pv:
        _required_number(a, 'pv_pu')
        if a > 1: raise ValueError('pv_pu > 1')
    for m in months:
        if isinstance(m, bool) or not isinstance(m, int) or m < 200001 or m % 100 not in range(1, 13):
            raise ValueError('Mês deve ser YYYYMM')
    dt = _required_number(phys['dt_hours'], 'dt_hours', positive=True)
    contract_cfg = cfg['contract']
    contract = ScenarioContract(
        scenario=contract_cfg['scenario'],
        discount_rate=_required_number(contract_cfg['discount_rate'], 'discount_rate'),
        horizon_years=int(contract_cfg['horizon_years']),
        pcc_cap_kw=_required_number(contract_cfg['pcc_cap_kw'], 'pcc_cap_kw', positive=True),
        economics_source=contract_cfg['economics_source'],
    )
    if contract.horizon_years < 1 or not contract.economics_source:
        raise ValueError('Horizonte/fonte econômica inválidos')
    econ = cfg['economic_inputs']
    if set(econ['annual_costs_excluding_grid']) != set(COST_KEYS) - {'energia_eletrica'}:
        raise ValueError('Todas as rubricas econômicas não elétricas são obrigatórias')
    if set(econ['initial_costs_excluding_grid']) != set(COST_KEYS) - {'energia_eletrica'}:
        raise ValueError('Todas as rubricas de investimento inicial são obrigatórias')
    for key, value in {**econ['annual_costs_excluding_grid'], **econ['initial_costs_excluding_grid']}.items():
        _required_number(value, key)
    capex_cfg = econ.get('variable_capex_brl_per_unit')
    if capex_cfg is not None:
        expected = {'pv_brl_per_kwp', 'bess_brl_per_kwh', 'pcs_brl_per_kw'}
        if not isinstance(capex_cfg, dict) or set(capex_cfg) != expected:
            raise ValueError('variable_capex_brl_per_unit exige exatamente pv_brl_per_kwp, bess_brl_per_kwh e pcs_brl_per_kw')
        for key, value in capex_cfg.items():
            _required_number(value, key)
        if not econ.get('variable_capex_source'):
            raise ValueError('Fonte dos coeficientes CAPEX variaveis obrigatoria')
    pkm = _required_number(econ['annual_pkm_verified'], 'annual_pkm_verified', positive=True)
    if not econ.get('provenance') or not econ.get('service_source'):
        raise ValueError('Proveniência econômica e de serviço obrigatórias')
    if cfg['execution_class'] == 'CONDITIONAL_RESEARCH' and cfg.get('inputs_homologated') is not True:
        raise ValueError('Execução científica bloqueada: inputs_homologated não confirmado')
    tariff_cfg = cfg['tariff']
    tariff = TariffEvidence(
        energy_tariff_brl_kwh=_required_number(tariff_cfg['energy_tariff_brl_kwh'], 'energy tariff'),
        demand_tariff_brl_kw_month=_required_number(tariff_cfg['demand_tariff_brl_kw_month'], 'demand tariff'),
        source=tariff_cfg['source'],
    )
    if not tariff.source: raise ValueError('Fonte tarifária ausente')
    design = cfg['design']
    names = ('pv_kwp', 'bess_kwh', 'pcs_kw')
    bounds = cfg['bounds']
    for name in names:
        low, high = bounds[name]
        _required_number(low, name + ' low')
        _required_number(high, name + ' high', positive=True)
        if high <= low: raise ValueError('Limites inválidos: ' + name)
    return cfg, contract, R0PhysicalInputs(load, pv, months, dt), tariff, econ, pkm, names, bounds


def run(config_path, output_dir):
    cfg, contract, physical, tariff, econ, pkm, names, bounds = load_contract(config_path)
    def economic_factory(op, bill, _contract):
        # Fatura calculada UMA VEZ a partir do despacho certificado do mesmo run.
        records = []
        for t in range(contract.horizon_years + 1):
            costs = dict(econ['initial_costs_excluding_grid'] if t == 0 else econ['annual_costs_excluding_grid'])
            costs['energia_eletrica'] = 0.0 if t == 0 else bill['total_bill_brl']
            if t == 0 and econ.get('variable_capex_brl_per_unit') is not None:
                unit = econ['variable_capex_brl_per_unit']
                design = op.design
                variable_capex = (
                    unit['pv_brl_per_kwp'] * _required_number(design['pv_kwp'], 'pv_kwp')
                    + unit['bess_brl_per_kwh'] * _required_number(design['bess_kwh'], 'bess_kwh')
                    + unit['pcs_brl_per_kw'] * _required_number(design['pcs_kw'], 'pcs_kw')
                )
                costs['infra_eletrica_capex'] += variable_capex
            provenance = {key: econ['provenance'] for key in COST_KEYS}
            if t == 0 and econ.get('variable_capex_brl_per_unit') is not None:
                provenance['infra_eletrica_capex'] = (
                    f"{econ['provenance']}; CAPEX_variavel={econ['variable_capex_source']}"
                )
            provenance['energia_eletrica'] = f"{tariff.source}; run={op.run_id}; despacho={op.dispatch_digest}"
            records.append(AnnualRecord(t, 0.0 if t == 0 else pkm, costs,
                                        service_verified=True, dispatch_feasible=True,
                                        provenance=provenance))
        return records
    providers = make_r0_integrated_providers(
        physical=physical, tariff=tariff, annual_economic_factory=economic_factory,
        pcc_cap_kw=contract.pcc_cap_kw)
    import numpy as np
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import ElementwiseProblem
    from pymoo.optimize import minimize
    history = []
    # Parametrizacao factivel da EQ-008: PCS <= 0.55 * BESS.
    # A terceira coordenada genetica e uma fracao u em [0,1], nao PCS em kW.
    pv_min, pv_max = map(float, bounds['pv_kwp'])
    bess_min, bess_max = map(float, bounds['bess_kwh'])
    pcs_min, pcs_max = map(float, bounds['pcs_kw'])
    bess_min = max(bess_min, pcs_min / 0.55)
    if bess_min > bess_max + 1e-10:
        raise ValueError('Regiao de projeto vazia: limites BESS/PCS incompatíveis com EQ-008')
    lo = np.array([pv_min, bess_min, 0.0], dtype=float)
    hi = np.array([pv_max, bess_max, 1.0], dtype=float)

    class Problem(ElementwiseProblem):
        def __init__(self):
            super().__init__(n_var=3, n_obj=2, n_ieq_constr=1, xl=lo, xu=hi)

        def _evaluate(self, x, out, *args, **kwargs):
            cid = f"{contract.scenario}_{len(history)+1:06d}"
            pv_kwp, bess_kwh, fraction = map(float, x)
            pcs_upper = min(pcs_max, 0.55 * bess_kwh)
            pcs_kw = pcs_min + fraction * max(0.0, pcs_upper - pcs_min)
            design = {'pv_kwp': pv_kwp, 'bess_kwh': bess_kwh, 'pcs_kw': pcs_kw}
            result = providers.evaluate(candidate_id=cid, design=design, contract=contract)
            mapped = nsga2_evaluation_rev02_3(result)
            out['F'] = mapped['F']
            out['G'] = mapped['G']
            history.append(result)
    ga = cfg['nsga2']
    population, generations = int(ga['population']), int(ga['generations'])
    if population < 4 or generations < 1: raise ValueError('NSGA-II: população >=4, gerações >=1')
    result = minimize(Problem(), NSGA2(pop_size=population), ('n_gen', generations),
                      seed=int(ga['seed']), verbose=False)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'historico.json').write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding='utf-8')
    valid = [r for r in history if r.get('status') == 'EVALUATED_CONDITIONAL']
    blocked = [r for r in history if r.get('status') != 'EVALUATED_CONDITIONAL']
    # Não confundir todos os avaliados com a frente não dominada.
    front = [r for r in valid if not any(
        (q['f1_integrado_brl_per_pkm'] <= r['f1_integrado_brl_per_pkm'] and
         q['f2_peak_pcc_kw'] <= r['f2_peak_pcc_kw'] and
         (q['f1_integrado_brl_per_pkm'] < r['f1_integrado_brl_per_pkm'] or
          q['f2_peak_pcc_kw'] < r['f2_peak_pcc_kw']))
        for q in valid)]
    (out / 'pareto_condicional.json').write_text(json.dumps(front, indent=2, ensure_ascii=False), encoding='utf-8')
    report = {'execution_class': cfg['execution_class'], 'architecture': 'R0',
              'scientific_homologation': False, 'evaluated': len(history),
              'conditionally_valid': len(valid), 'blocked': len(blocked),
              'pareto_count': len(front), 'input': str(config_path),
              'warning': 'Exemplo sintético ou avaliação condicional; não representa resultados D28 homologados.'}
    (out / 'resumo.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description='Execução integrada D28 R0 (NSGA-II + HiGHS + F1/F2)')
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.output), indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
