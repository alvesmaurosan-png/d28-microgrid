"""F1 integrado: composição auditável; não infere CAPEX ausente."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class IntegratedCosts:
    fleet_brl: float
    infrastructure_brl: float
    grid_reinforcement_brl: float
    energy_brl: float
    operations_brl: float
    residual_brl: float
    discounted_pkm: float

    def f1_brl_per_pkm(self) -> float:
        v = vars(self)
        if any(not math.isfinite(float(x)) or float(x) < 0 for x in v.values()):
            raise ValueError("Custos e PKM devem ser finitos e não negativos")
        if self.discounted_pkm <= 0:
            raise ValueError("PKM descontado não homologado")
        numerator = (self.fleet_brl + self.infrastructure_brl +
                     self.grid_reinforcement_brl + self.energy_brl +
                     self.operations_brl - self.residual_brl)
        if numerator < 0:
            raise ValueError("VP líquido negativo requer auditoria")
        return numerator / self.discounted_pkm
