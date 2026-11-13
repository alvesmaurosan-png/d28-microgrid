"""M5: não fabricar F1/F3 sem entradas auditadas."""
def f2_peak_pcc(grid_kw):
    if not grid_kw:raise ValueError('PCC vazio')
    return max(grid_kw)

def f1_cost_per_pkm(*,pv_cost_brl,discounted_pkm):
    if pv_cost_brl is None or discounted_pkm is None or discounted_pkm<=0:raise ValueError('F1 bloqueada: VPL ou PKM não auditado')
    return pv_cost_brl/discounted_pkm

def f3_ghg_per_pkm(*,lifecycle_kgco2e,pkm):
    if lifecycle_kgco2e is None or pkm is None or pkm<=0:raise ValueError('F3 bloqueada: inventário ACV ou PKM incompleto')
    return lifecycle_kgco2e/pkm
