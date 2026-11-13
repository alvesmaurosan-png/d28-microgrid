from dataclasses import dataclass
from math import isfinite

ARCHITECTURES = ("R0", "R1", "R2", "R3")

@dataclass(frozen=True)
class ScientificEvidence:
    architecture: str
    scenario: str
    temporal_intervals: int
    interval_hours: float
    dispatch_optimal: bool
    physics_validated: bool
    individual_charging_validated: bool
    f1_brl_per_pkm: float | None = None
    f2_kw: float | None = None
    f3_kgco2e_per_pkm: float | None = None
    f1_homologated: bool = False
    f2_homologated: bool = False
    f3_homologated: bool = False
    lca_complete: bool = False
    source_manifest_sha256: str | None = None

def valid(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and value >= 0
    )

def assess(e):
    if e.architecture not in ARCHITECTURES:
        raise ValueError("Arquitetura desconhecida")

    reasons = []

    if e.temporal_intervals != 35040 or e.interval_hours != 0.25:
        reasons.append("ANNUAL_15MIN_NOT_VALIDATED")
    if not e.dispatch_optimal:
        reasons.append("MILP_NOT_OPTIMAL")
    if not e.physics_validated:
        reasons.append("PHYSICS_NOT_VALIDATED")
    if not e.individual_charging_validated:
        reasons.append("INDIVIDUAL_CHARGING_NOT_VALIDATED")

    h = e.source_manifest_sha256
    if not h or len(h) != 64 or any(c not in "0123456789abcdefABCDEF" for c in h):
        reasons.append("INPUT_MANIFEST_SHA256_MISSING")

    base = not reasons

    f1 = base and e.f1_homologated and valid(e.f1_brl_per_pkm)
    f2 = base and e.f2_homologated and valid(e.f2_kw)
    f3 = (
        base and e.f3_homologated
        and e.lca_complete and valid(e.f3_kgco2e_per_pkm)
    )

    if not f1:
        reasons.append("F1_NOT_ELIGIBLE")
    if not f2:
        reasons.append("F2_NOT_ELIGIBLE")
    if not f3:
        reasons.append("F3_NOT_ELIGIBLE_OR_LCA_INCOMPLETE")

    return {
        "architecture_id": e.architecture,
        "scenario_id": e.scenario,
        "F1_brl_per_pkm": e.f1_brl_per_pkm if f1 else None,
        "F2_kw": e.f2_kw if f2 else None,
        "F3_kgco2e_per_pkm": e.f3_kgco2e_per_pkm if f3 else None,
        "F1_status": "VALIDATED" if f1 else "BLOCKED",
        "F2_status": "VALIDATED" if f2 else "BLOCKED",
        "F3_status": "VALIDATED" if f3 else "BLOCKED",
        "eligible_pareto_f1_f2": f1 and f2,
        "eligible_pareto_3d": f1 and f2 and f3,
        "reasons": reasons,
    }
