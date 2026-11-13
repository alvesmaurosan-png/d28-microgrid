"""Contratos executáveis, sem homologar parâmetros desconhecidos."""
from dataclasses import dataclass
from enum import Enum
import math

class Scenario(str, Enum):
    BAU = "BAU"
    REALISTA = "Realista"
    C1 = "Cenario_1"
    C2 = "Cenario_2"

FLEET_REFERENCE = {2026: 100, 2030: 300, 2038: 450}
TOTAL_FLEET = 450
PCC_LIMIT_KW = 2500.0

@dataclass(frozen=True)
class ScenarioContract:
    scenario: Scenario
    year: int
    planned_bev: int
    total_fleet: int
    pcc_limit_kw: float | None
    grid_upgrade_allowed: bool
    local_pv_bess_chp: bool
    fleet_mix_optimizable: bool
    enforce_all_bev_in_2038: bool


def contract(scenario: Scenario | str, year: int) -> ScenarioContract:
    s = Scenario(scenario)
    if year not in FLEET_REFERENCE:
        raise ValueError("Ano não previsto pelo PC-REV08/REV02")
    return ScenarioContract(s, year, FLEET_REFERENCE[year], TOTAL_FLEET,
        None if s == Scenario.BAU else PCC_LIMIT_KW,
        s == Scenario.BAU, s in (Scenario.C1, Scenario.C2),
        s == Scenario.C2, s in (Scenario.BAU, Scenario.C1))


def validate_fleet(bev: int, diesel: int, gas: int, *, total: int = TOTAL_FLEET):
    if any(not isinstance(x, int) or x < 0 for x in (bev, diesel, gas)):
        raise ValueError("Contagens de frota devem ser inteiros não negativos")
    if bev + diesel + gas != total:
        raise ValueError("Frota física deve totalizar 450 ônibus")


def validate_design(design: dict, limits: dict):
    for k in ("pv_kw", "bess_kwh", "pcs_kw", "chp_kw"):
        v = float(design.get(k, 0))
        upper = limits.get(k)
        if not math.isfinite(v) or v < 0 or upper is None or not math.isfinite(float(upper)) or v > float(upper):
            raise ValueError(f"Projeto fora do domínio homologado: {k}")
    if float(design.get("pcs_kw", 0)) > float(limits.get("c_rate", 0)) * float(design.get("bess_kwh", 0)) + 1e-8:
        raise ValueError("PCS excede C-rate")
