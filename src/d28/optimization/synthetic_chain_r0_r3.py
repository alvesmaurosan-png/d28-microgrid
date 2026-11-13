"""Gate sintético: dimensionamento -> MILP -> indicadores de horizonte.

Valores são hipóteses EXPLÍCITAS do teste, não parâmetros D28 homologados.
F1 = custo energético do horizonte / PKM do horizonte; F2 = pico PCC;
F3 = emissões do horizonte / PKM do horizonte. Não anualiza nem executa NSGA-II.
"""
from dataclasses import dataclass
import math
from d28.optimization.r0_r3_bridge import build_architecture, solve_highs

@dataclass(frozen=True)
class SyntheticInputs:
    pkm_horizon: float
    grid_brl_per_kwh: float
    grid_kgco2e_per_kwh: float
    fuel_brl_per_nm3: float
    fuel_kgco2e_per_nm3: float
    equipment_cost_brl_horizon: float
    equipment_kgco2e_horizon: float
    cgob_kgco2e_credit_horizon: float = 0.0


def _check(inputs, route):
    for name, value in vars(inputs).items():
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'Entrada sintética inválida: {name}')
    if inputs.pkm_horizon <= 0:
        raise ValueError('PKM do horizonte deve ser positivo')
    if inputs.cgob_kgco2e_credit_horizon != 0:
        raise ValueError('Crédito CGOB não autorizado neste gate sintético')
    if route not in ('R0','R1','R2','R3'):
        raise ValueError('Rota desconhecida')


def evaluate_synthetic(route, *, common, inputs, chp=None, biogas=None, cgob=None,
                       solver_name='appsi_highs'):
    """Calcula indicadores somente para o horizonte fornecido; nunca F1/F3 anuais."""
    _check(inputs, route)
    model = build_architecture(route, common=common, chp=chp, biogas=biogas, cgob=cgob)
    solved = solve_highs(model, solver_name=solver_name)
    if not solved['optimal']:
        raise RuntimeError(f'MILP não ótimo: {solved["termination"]}')
    import pyomo.environ as p
    dt = float(common['dt_hours'])
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError('Passo temporal inválido')
    grid = [float(p.value(model.grid[t])) for t in model.T]
    if not grid or any(not math.isfinite(x) or x < -1e-7 for x in grid):
        raise ValueError('Despacho da rede inválido')
    grid_kwh = sum(grid)*dt
    fuel_nm3 = sum(float(p.value(model.chp.fuel_nm3[t])) for t in model.T) if route != 'R0' else 0.0
    # Não incluir CGOB como combustível nem presumir abatimento de emissões.
    cost = (grid_kwh*inputs.grid_brl_per_kwh + fuel_nm3*inputs.fuel_brl_per_nm3
            + inputs.equipment_cost_brl_horizon)
    ghg = (grid_kwh*inputs.grid_kgco2e_per_kwh + fuel_nm3*inputs.fuel_kgco2e_per_nm3
           + inputs.equipment_kgco2e_horizon)
    f1, f2, f3 = cost/inputs.pkm_horizon, max(grid), ghg/inputs.pkm_horizon
    if any(not math.isfinite(v) or v < 0 for v in (f1,f2,f3)):
        raise ValueError('Indicadores sintéticos inválidos')
    return {'route':route,'scope':'SYNTHETIC_HORIZON_NOT_ANNUAL',
            'scientific_objectives_validated':False,'nsga2_released':False,
            'objectives':{'F1_BRL_per_pkm':f1,'F2_kW':f2,'F3_kgCO2e_per_pkm':f3},
            'audit':{'grid_kwh':grid_kwh,'fuel_nm3':fuel_nm3,'peak_pcc_kw':f2,
                     'cost_brl_horizon':cost,'emissions_kgco2e_horizon':ghg,
                     'pkm_horizon':inputs.pkm_horizon,'dt_hours':dt,
                     'assumptions':vars(inputs), 'solver':solved,
                     'cgob_rule':'no_credit_assumed',
                     'annual_contract':'NOT_APPLIED_SYNTHETIC_ONLY'}}
