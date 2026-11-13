"""Adaptador REV05: construtores reais R0-R3, sem homologacao implicita."""
from collections.abc import Mapping
from d28.optimization.d28_scientific_bridge import evaluate_candidate
from d28.optimization.annual_lexicographic_dispatch import solve_annual_lexicographic

ROUTES = frozenset(('R0','R1','R2','R3'))


def build_route_model(route, design, *, common, chp=None, biogas=None, cgob=None):
    """Usa o roteador existente; preserva as assinaturas e validacoes originais."""
    if route not in ROUTES:
        raise ValueError(f'Arquitetura invalida: {route}')
    if not isinstance(design, Mapping):
        raise TypeError('design deve ser um mapeamento')
    if not isinstance(common, Mapping):
        raise TypeError('common deve ser um mapeamento')
    from d28.optimization.r0_r3_bridge import build_architecture
    # As variaveis do design prevalecem sobre defaults comuns.
    overlap = set(common).intersection(design)
    if overlap:
        raise ValueError(f'Campos ambiguos common/design: {sorted(overlap)}')
    return build_architecture(route, common={**common, **design},
                              chp=chp, biogas=biogas, cgob=cgob)


def evaluate_route_candidate(route, design, *, common, chp=None, biogas=None,
                             cgob=None, compute_f1=None, compute_f3=None,
                             evidence=None, expected_intervals=35040,
                             dt_hours=0.25, solver_name='appsi_highs'):
    """Nao cria tarifas, PKM, fatores LCA nem homologacoes ficticias."""
    return evaluate_candidate(
        route, design,
        build_model=lambda r,d: build_route_model(r,d,common=common,
                            chp=chp,biogas=biogas,cgob=cgob),
        solve_dispatch=lambda model,dt_hours: solve_annual_lexicographic(
                            model,dt_hours=dt_hours,solver_name=solver_name),
        compute_f1=compute_f1,compute_f3=compute_f3,
        evidence=evidence,expected_intervals=expected_intervals,
        dt_hours=dt_hours)
