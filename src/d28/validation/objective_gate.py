"""Contrato de objetivos: ausência de F3/PKM bloqueia Pareto 3D."""
import math

def objective_triplet(f1_brl_per_pkm, f2_kw, f3_kgco2e_per_pkm):
    vals=(f1_brl_per_pkm,f2_kw,f3_kgco2e_per_pkm)
    if any(x is None for x in vals):
        raise ValueError("F1, F2 e F3 devem estar completos; não substituir por zero")
    values=tuple(float(x) for x in vals)
    if any(not math.isfinite(x) or x<0 for x in values):
        raise ValueError("Objetivos inválidos")
    return values
