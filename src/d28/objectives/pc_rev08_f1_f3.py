"""PC-REV08 EQ-040/EQ-045: objective arithmetic only; no dispatch modification.
No annualization, factor substitution, or silent zero for missing inventory.
"""
from __future__ import annotations
import math

YEARS = 20
RATE = .12
REQUIRED_LCA = ('D11-014','D11-015','D11-016','D11-018','D11-019')


def number(name, value, *, nonnegative=False):
    if value is None or isinstance(value, bool):
        raise ValueError(f'{name}: missing numeric evidence')
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{name}: invalid numeric value') from None
    if not math.isfinite(result) or (nonnegative and result < 0):
        raise ValueError(f'{name}: nonfinite or negative')
    return result


def f1_pc_rev08(cf0_brl, annual_cashflows_brl, annual_pkm, *, rate=RATE):
    """EQ-040. Exactly 20 explicitly supplied annual cashflows and PKM."""
    if len(annual_cashflows_brl) != YEARS or len(annual_pkm) != YEARS:
        raise ValueError('EQ-040 requires 20 annual cashflows and 20 annual PKM')
    rate = number('real_discount_rate', rate)
    if rate <= -1:
        raise ValueError('invalid discount rate')
    initial = number('CF_0', cf0_brl)
    pv_cost = initial + sum(number(f'CF_{y}', c)/(1+rate)**y
                            for y,c in enumerate(annual_cashflows_brl,1))
    pv_service = sum(number(f'PKM_{y}', p, nonnegative=True)/(1+rate)**y
                     for y,p in enumerate(annual_pkm,1))
    if pv_service <= 0:
        raise ValueError('present value of PKM must be positive')
    return {'F1_brl2026_per_pkm':pv_cost/pv_service,
            'pv_cost_brl2026':pv_cost, 'pv_pkm':pv_service,
            'discount_rate_real':rate,'years':YEARS,'equation':'PC-REV08 EQ-040'}


def f3_pc_rev08(*, ghg_components_kgco2e, annual_pkm, factor_evidence,
                  approved_credits_kgco2e=0):
    """EQ-045. Requires complete nonoverlapping inventory and evidence of missing factors.

    ghg_components_kgco2e must have exactly the six disjoint buckets; assets
    must EXCLUDE replacements and EOL to prevent double counting.
    """
    missing = [k for k in REQUIRED_LCA if not factor_evidence.get(k)]
    if missing:
        raise ValueError('F3_BLOCKED_MISSING_LCA_FACTORS: '+','.join(missing))
    buckets = ('assets','replacements','operation','upstream','fugitive','eol')
    if set(ghg_components_kgco2e) != set(buckets):
        raise ValueError('EQ-045 requires six distinct lifecycle buckets')
    if not factor_evidence.get('boundary_nonoverlap_documented'):
        raise ValueError('F3_BLOCKED_BOUNDARY_OVERLAP_NOT_DOCUMENTED')
    if len(annual_pkm) != YEARS:
        raise ValueError('EQ-045 requires 20 annual PKM')
    pkm = sum(number(f'PKM_{y}',v,nonnegative=True) for y,v in enumerate(annual_pkm,1))
    if pkm <= 0:
        raise ValueError('total PKM must be positive')
    emissions = sum(number(k,ghg_components_kgco2e[k],nonnegative=True) for k in buckets)
    credits = number('approved_credits_kgco2e',approved_credits_kgco2e,nonnegative=True)
    return {'F3_kgco2e_per_pkm':(emissions-credits)/pkm,
            'ghg_total_kgco2e':emissions-credits,'pkm_total':pkm,
            'equation':'PC-REV08 EQ-045'}


def base_master_status(records):
    """Read-only status: absence of factor values is never replaced by zero."""
    by_id = {r['id']:r for r in records}
    return {id_: {'value_raw':by_id[id_]['value_raw'],
                  'unit':by_id[id_]['unit'],
                  'evidence_status':by_id[id_]['evidence_status']}
            for id_ in REQUIRED_LCA}
