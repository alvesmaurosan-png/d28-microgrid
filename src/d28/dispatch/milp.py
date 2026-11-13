"""M2: protótipo R0 agregado, explicitamente NÃO científico."""
def build_r0_smoke(load_kw, pv_pu, pv_capacity_kw, pcc_cap_kw=2500.0):
    import pyomo.environ as p
    if len(load_kw)!=len(pv_pu) or not load_kw:raise ValueError('Séries inválidas')
    m=p.ConcreteModel();m.T=p.RangeSet(0,len(load_kw)-1)
    m.grid=p.Var(m.T,domain=p.NonNegativeReals,bounds=(0,pcc_cap_kw))
    m.pv=p.Var(m.T,domain=p.NonNegativeReals)
    m.pv_cap=p.Constraint(m.T,rule=lambda m,t:m.pv[t]<=pv_capacity_kw*float(pv_pu[t]))
    m.balance=p.Constraint(m.T,rule=lambda m,t:m.grid[t]+m.pv[t]==float(load_kw[t]))
    m.obj=p.Objective(expr=sum(m.grid[t] for t in m.T),sense=p.minimize)
    return m

def build_r0_milp(
    load_kw,
    pv_pu,
    pv_capacity_kw,
    bess_capacity_kwh,
    pcs_power_kw,
    *,
    soh=1.0,
    pcc_cap_kw=2500.0,
    dt_hours=0.25,
    eta_charge=0.922,
    eta_discharge=0.922,
    initial_soc=0.50,
    terminal_policy="free",
    terminal_energy_kwh=None,
    pv_capacity_max_kwp=None,
):
    """Constrói MILP R0 agregado sintético (EQ-001 a EQ-010, escopo PV+BESS).

    load_kw representa a demanda AC total, sem dupla contagem de recarga.
    pv_pu é uma série específica previamente validada (kW/kWp); não se
    aplica fator de geração adicional. Sem CHP, exportação ou déficit.

    terminal_policy: 'free', 'cyclic' ou 'fixed'. A opção 'cyclic' só pode
    ser escolhida se o horizonte justificar fechamento cíclico (EQ-009).
    SOH é exógeno; política de reposição não é inferida (EQ-010).
    """
    import math
    import pyomo.environ as p

    try:
        loads = [float(x) for x in load_kw]
        solar = [float(x) for x in pv_pu]
    except (TypeError, ValueError) as exc:
        raise ValueError("Séries de demanda e PV devem ser numéricas") from exc
    if not loads or len(loads) != len(solar):
        raise ValueError("Séries vazias ou com comprimentos diferentes")
    if not all(math.isfinite(x) and x >= 0 for x in loads + solar):
        raise ValueError("Séries devem ser finitas e não negativas")

    values = {
        "pv_capacity_kw": pv_capacity_kw,
        "bess_capacity_kwh": bess_capacity_kwh,
        "pcs_power_kw": pcs_power_kw,
        "soh": soh,
        "pcc_cap_kw": pcc_cap_kw,
        "dt_hours": dt_hours,
        "eta_charge": eta_charge,
        "eta_discharge": eta_discharge,
        "initial_soc": initial_soc,
    }
    if pv_capacity_max_kwp is not None:
        values["pv_capacity_max_kwp"] = pv_capacity_max_kwp
    try:
        values = {key: float(value) for key, value in values.items()}
    except (TypeError, ValueError) as exc:
        raise ValueError("Parâmetros numéricos inválidos") from exc
    if not all(math.isfinite(v) for v in values.values()):
        raise ValueError("Parâmetros devem ser finitos")
    pv_capacity_kw = values["pv_capacity_kw"]
    bess_capacity_kwh = values["bess_capacity_kwh"]
    pcs_power_kw = values["pcs_power_kw"]
    soh = values["soh"]
    pcc_cap_kw = values["pcc_cap_kw"]
    dt_hours = values["dt_hours"]
    eta_charge = values["eta_charge"]
    eta_discharge = values["eta_discharge"]
    initial_soc = values["initial_soc"]
    if min(pv_capacity_kw, bess_capacity_kwh, pcs_power_kw, pcc_cap_kw) < 0:
        raise ValueError("Capacidades e PCC não podem ser negativos")
    if not (0 < soh <= 1):
        raise ValueError("SOH deve estar em (0, 1]")
    if dt_hours <= 0:
        raise ValueError("dt_hours deve ser positivo")
    if not (0 < eta_charge <= 1 and 0 < eta_discharge <= 1):
        raise ValueError("Eficiências devem estar em (0, 1]")
    if not (0.10 <= initial_soc <= 0.90):
        raise ValueError("SOC inicial deve estar em [0.10, 0.90]")
    if pcs_power_kw > 0.55 * bess_capacity_kwh + 1e-9:
        raise ValueError("PCS excede 0,55 da capacidade BESS (EQ-008)")
    if pv_capacity_max_kwp is not None and pv_capacity_kw > values["pv_capacity_max_kwp"] + 1e-9:
        raise ValueError("Capacidade FV excede teto geométrico informado")
    if pv_capacity_max_kwp is not None and values["pv_capacity_max_kwp"] < 0:
        raise ValueError("Teto geométrico inválido")
    if terminal_policy not in ("free", "cyclic", "fixed"):
        raise ValueError("terminal_policy deve ser free, cyclic ou fixed")
    if terminal_policy == "fixed":
        if terminal_energy_kwh is None:
            raise ValueError("fixed requer terminal_energy_kwh")
        try:
            terminal_energy_kwh = float(terminal_energy_kwh)
        except (TypeError, ValueError) as exc:
            raise ValueError("Energia terminal inválida") from exc
        if not math.isfinite(terminal_energy_kwh) or not (
            0.10 * bess_capacity_kwh * soh - 1e-9 <= terminal_energy_kwh
            <= 0.90 * bess_capacity_kwh * soh + 1e-9
        ):
            raise ValueError("Energia terminal fora da faixa SOC")
    elif terminal_energy_kwh is not None:
        raise ValueError("terminal_energy_kwh só é permitido com terminal_policy='fixed'")

    n = len(loads)
    capacity_usable = bess_capacity_kwh * soh
    m = p.ConcreteModel(name="R0_PV_BESS_synthetic")
    m.T = p.RangeSet(0, n - 1)
    m.S = p.RangeSet(0, n)  # estados incluem o instante terminal
    m.load_kw = p.Param(m.T, initialize=dict(enumerate(loads)))
    m.pv_pu = p.Param(m.T, initialize=dict(enumerate(solar)))
    m.grid = p.Var(m.T, domain=p.NonNegativeReals, bounds=(0, pcc_cap_kw))
    m.pv = p.Var(m.T, domain=p.NonNegativeReals)
    m.pv_curt = p.Var(m.T, domain=p.NonNegativeReals)
    m.bess_charge = p.Var(m.T, domain=p.NonNegativeReals)
    m.bess_discharge = p.Var(m.T, domain=p.NonNegativeReals)
    m.bess_mode = p.Var(m.T, domain=p.Binary)
    m.bess_energy = p.Var(m.S, domain=p.NonNegativeReals,
                          bounds=(0.10 * capacity_usable, 0.90 * capacity_usable))

    m.balance = p.Constraint(
        m.T,
        rule=lambda m, t: m.grid[t] + m.pv[t] + m.bess_discharge[t]
        == m.load_kw[t] + m.bess_charge[t],
    )
    m.pv_accounting = p.Constraint(
        m.T, rule=lambda m, t: m.pv[t] + m.pv_curt[t] == pv_capacity_kw * m.pv_pu[t]
    )
    m.bess_energy_balance = p.Constraint(
        m.T,
        rule=lambda m, t: m.bess_energy[t + 1]
        == m.bess_energy[t]
        + eta_charge * m.bess_charge[t] * dt_hours
        - m.bess_discharge[t] * dt_hours / eta_discharge,
    )
    m.bess_charge_limit = p.Constraint(
        m.T, rule=lambda m, t: m.bess_charge[t] <= pcs_power_kw * m.bess_mode[t]
    )
    m.bess_discharge_limit = p.Constraint(
        m.T, rule=lambda m, t: m.bess_discharge[t] <= pcs_power_kw * (1 - m.bess_mode[t])
    )
    m.bess_initial = p.Constraint(expr=m.bess_energy[0] == initial_soc * capacity_usable)
    if terminal_policy == "cyclic":
        m.bess_terminal = p.Constraint(expr=m.bess_energy[n] == m.bess_energy[0])
    elif terminal_policy == "fixed":
        m.bess_terminal = p.Constraint(expr=m.bess_energy[n] == terminal_energy_kwh)
    # Objetivo operacional provisório: energia importada [kWh].
    m.obj = p.Objective(expr=dt_hours * sum(m.grid[t] for t in m.T), sense=p.minimize)
    m._r0_metadata = {
        "scientific_validation": False,
        "dt_hours": dt_hours,
        "soh": soh,
        "terminal_policy": terminal_policy,
        "scope": "synthetic_aggregate_PV_BESS_no_CHP",
    }
    return m
