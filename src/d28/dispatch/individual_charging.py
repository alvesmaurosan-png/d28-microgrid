"""Acoplamento de recarga ao MILP sem dupla contagem REV09."""
import math

def attach_individual_charging(model, *, mode, sessions=(), base_load_kw=None,
                               charger_efficiency=None, charger_power_kw=None,
                               vehicle_energy_kwh=None, vehicle_initial_kwh=None,
                               vehicle_min_kwh=None, vehicle_max_kwh=None,
                               route_energy_kwh=None, dt_hours=None):
    if mode == "aggregated_rev09":
        if sessions or base_load_kw is not None:
            raise ValueError("REV09 agregada não admite recarga adicional")
        return model
    if mode != "individual":raise ValueError("Modo de demanda inválido")
    import pyomo.environ as p
    if getattr(model,'_individual_charging_attached',False):raise ValueError("Recarga já acoplada")
    T=list(model.T);n=len(T);dt=float(dt_hours or model._r0_metadata['dt_hours'])
    if dt<=0 or base_load_kw is None or len(base_load_kw)!=n or not sessions:
        raise ValueError("Recarga individual exige carga de base e sessões completas")
    base=[float(v) for v in base_load_kw]
    if any(not math.isfinite(v) or v<0 for v in base):raise ValueError("Carga de base inválida")
    ids=[str(s['session_id']) for s in sessions]
    if len(set(ids))!=len(ids):raise ValueError("Sessões duplicadas")
    chargers=sorted({str(s['charger_id']) for s in sessions})
    vehicles=sorted({str(s['vehicle_id']) for s in sessions})
    if any(x is None for x in (charger_efficiency,charger_power_kw,vehicle_initial_kwh,vehicle_min_kwh,vehicle_max_kwh,route_energy_kwh)):
        raise ValueError("Faltam parâmetros individuais de recarga e SOC")
    for v in vehicles:
        if not (0<=vehicle_min_kwh[v]<=vehicle_initial_kwh[v]<=vehicle_max_kwh[v]):
            raise ValueError("SOC inicial/limites inválidos")
    for c in chargers:
        if not(0<float(charger_efficiency[c])<=1 and float(charger_power_kw[c])>0):
            raise ValueError("Carregador inválido")
    S={s['session_id']:s for s in sessions}
    for s in sessions:
        if s['vehicle_id'] not in vehicles or s['charger_id'] not in chargers:
            raise ValueError("Sessão inválida")
        allowed=list(s['allowed_intervals'])
        if not allowed or any(t not in T for t in allowed):raise ValueError("Janela inválida")
        if float(s['required_dc_kwh'])<0:raise ValueError("Energia inválida")
    m=model
    m.CHS=p.Set(initialize=ids)
    m.VEH=p.Set(initialize=vehicles)
    m.CHR=p.Set(initialize=chargers)
    allowed={(sid,t) for sid,s in S.items() for t in s['allowed_intervals']}
    m.CHT=p.Set(dimen=2,initialize=sorted(allowed))
    m.charge_dc=p.Var(m.CHT,domain=p.NonNegativeReals)
    m.charge_active=p.Var(m.CHT,domain=p.Binary)
    m.charge_power_limit=p.Constraint(m.CHT,rule=lambda m,sid,t:
        m.charge_dc[sid,t]<=float(charger_power_kw[S[sid]['charger_id']])*m.charge_active[sid,t])
    m.charger_exclusive=p.Constraint(m.CHR,m.T,rule=lambda m,c,t:
        sum(m.charge_active[sid,t] for sid in ids if S[sid]['charger_id']==c and (sid,t) in allowed)<=1)
    m.session_energy=p.Constraint(m.CHS,rule=lambda m,sid:
        dt*sum(m.charge_dc[sid,t] for t in S[sid]['allowed_intervals'])>=float(S[sid]['required_dc_kwh']))
    m.veh_soc=p.Var(m.VEH,range(n+1),domain=p.NonNegativeReals)
    m.veh_initial=p.Constraint(m.VEH,rule=lambda m,v:m.veh_soc[v,0]==float(vehicle_initial_kwh[v]))
    m.veh_min=p.Constraint(m.VEH,range(n+1),rule=lambda m,v,t:m.veh_soc[v,t]>=float(vehicle_min_kwh[v]))
    m.veh_max=p.Constraint(m.VEH,range(n+1),rule=lambda m,v,t:m.veh_soc[v,t]<=float(vehicle_max_kwh[v]))
    m.veh_transition=p.Constraint(m.VEH,m.T,rule=lambda m,v,t:
        m.veh_soc[v,t+1]==m.veh_soc[v,t]
        +dt*sum(m.charge_dc[sid,t] for sid in ids if S[sid]['vehicle_id']==v and (sid,t) in allowed)
        -float(route_energy_kwh.get((v,t),0)))
    m.del_component(m.balance)
    def balance(m,t):
        charging=sum(m.charge_dc[sid,t]/float(charger_efficiency[S[sid]['charger_id']])
                     for sid in ids if (sid,t) in allowed)
        chp=m.chp.power_gross_kw[t] if hasattr(m,'chp') else 0
        aux=m.auxiliary_load_kw[t] if hasattr(m,'auxiliary_load_kw') else 0
        return m.grid[t]+m.pv[t]+m.bess_discharge[t]+chp==base[t]+charging+m.bess_charge[t]+aux
    m.balance=p.Constraint(m.T,rule=balance)
    m._individual_charging_attached=True
    m._r0_metadata.update(demand_mode='individual',scientific_validation=False)
    return m
