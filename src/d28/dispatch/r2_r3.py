"""Extensões R2/R3 não destrutivas; parâmetros explícitos, sem inventar valores."""
import math

def _finite_positive(name, value, allow_zero=False):
    v=float(value)
    if not math.isfinite(v) or (v<0 if allow_zero else v<=0):
        raise ValueError(f"{name} inválido")
    return v

def build_r3_milp(*args, cgob_coverage_nm3=None, **kwargs):
    """R3: despacho físico idêntico ao R1; CGOB é atributo separado, não combustível."""
    from d28.dispatch.r1 import build_r1_milp
    model=build_r1_milp(*args,**kwargs)
    if cgob_coverage_nm3 is not None:
        coverage=_finite_positive("CGOB",cgob_coverage_nm3,True)
        import pyomo.environ as p
        model.cgob_coverage_nm3=p.Param(initialize=coverage)
        model.cgob_coverage_limit=p.Constraint(
            expr=model.cgob_coverage_nm3 <= sum(model.chp.fuel_nm3[t] for t in model.T))
    model._r0_metadata.update(architecture="R3",cgob_attribute_only=True,
                              scientific_validation=False)
    return model

def build_r2_milp(*args, production_nm3, gasometer_capacity_nm3,
                  initial_gas_nm3, terminal_gas_policy="cyclic",
                  auxiliary_kw=None, auxiliary_fraction_chp_gross=None,
                  minimum_load_fraction=0.50, digester_capacity_m3=None,
                  substrate_t_per_day=None, physical_evidence=None, **kwargs):
    """R2: CHP a biogás, gasômetro e auxiliares; produção exógena documentada.
    Não representa ainda o dimensionamento endógeno do biodigestor.
    """
    import pyomo.environ as p
    from d28.dispatch.milp import build_r0_milp
    from d28.dispatch.chp import attach_chp_constraints
    required=("chp_capacity_kw","electrical_efficiency","fuel_lhv_kwh_per_nm3","availability")
    if any(k not in kwargs for k in required):
        raise ValueError("R2 exige CHP, eficiência, PCI do biogás e disponibilidade")
    chp_options={k:kwargs.pop(k) for k in required}
    # Injeção de substrato/volume não pode ser meramente decorativa.
    if substrate_t_per_day is not None or digester_capacity_m3 is not None:
        if substrate_t_per_day is None or digester_capacity_m3 is None:
            raise ValueError('R2: substrato e volume devem ser fornecidos juntos')
        from d28.traceability.r2_closure import validate_r2_inputs
        validate_r2_inputs(production_nm3=production_nm3,
            substrate_t_per_day=substrate_t_per_day,
            digester_capacity_m3=digester_capacity_m3,
            gasometer_capacity_nm3=gasometer_capacity_nm3,
            chp_capacity_kw=chp_options['chp_capacity_kw'],
            electrical_efficiency=chp_options['electrical_efficiency'],
            fuel_lhv_kwh_per_nm3=chp_options['fuel_lhv_kwh_per_nm3'],
            dt_hours=kwargs.get('dt_hours',0.25),physical_evidence=physical_evidence)
    elif physical_evidence is not None:
        raise ValueError('R2: evidência sem substrato/volume não é aplicável')
    model=build_r0_milp(*args,**kwargs)
    periods=list(model.T); n=len(periods)
    prod=[_finite_positive("produção",x,True) for x in production_nm3]
    if auxiliary_kw is not None and auxiliary_fraction_chp_gross is not None:
        raise ValueError("Auxiliares exógenos e proporcionais são mutuamente exclusivos")
    aux=[_finite_positive("auxiliar",x,True) for x in (auxiliary_kw if auxiliary_kw is not None else [0]*n)]
    if auxiliary_fraction_chp_gross is not None:
        auxiliary_fraction_chp_gross = _finite_positive("fração auxiliar",auxiliary_fraction_chp_gross,True)
        if auxiliary_fraction_chp_gross >= 1:
            raise ValueError("Fração auxiliar deve ser inferior a 1")
    if digester_capacity_m3 is not None:
        _finite_positive("volume digestor",digester_capacity_m3)
    if substrate_t_per_day is not None:
        _finite_positive("substrato diário",substrate_t_per_day)
    cap=_finite_positive("gasômetro",gasometer_capacity_nm3)
    initial=_finite_positive("estoque inicial",initial_gas_nm3,True)
    if len(prod)!=n or len(aux)!=n or initial>cap:raise ValueError("Séries/estoque de R2 inválidos")
    if terminal_gas_policy not in ("cyclic","free"):raise ValueError("Política terminal inválida")
    chp=attach_chp_constraints(model,architecture="R1",
        minimum_load_fraction=minimum_load_fraction,**chp_options)
    if auxiliary_fraction_chp_gross is not None:
        model.auxiliary_load_kw=p.Expression(model.T,rule=lambda m,t:
            auxiliary_fraction_chp_gross*m.chp.power_gross_kw[t])
    else:
        model.auxiliary_load_kw=p.Param(model.T,initialize=dict(zip(periods,aux)),within=p.NonNegativeReals)
    model.del_component(model.balance)
    model.balance=p.Constraint(model.T,rule=lambda m,t:
        m.grid[t]+m.pv[t]+m.bess_discharge[t]+m.chp.power_gross_kw[t]
        ==m.load_kw[t]+m.bess_charge[t]+m.auxiliary_load_kw[t])
    model.gas_stock=p.Var(range(n+1),bounds=(0,cap))
    # O fluxo livre é descarte operacional, NÃO perda física ou vazamento.
    model.gas_curtailment=p.Var(model.T,domain=p.NonNegativeReals)
    # Alias legado para relatórios anteriores; nunca interpretar como fuga.
    model.gas_loss=p.Reference(model.gas_curtailment[:])
    model.gas_initial=p.Constraint(expr=model.gas_stock[0]==initial)
    model.gas_transition=p.Constraint(model.T,rule=lambda m,t:
        m.gas_stock[t+1]==m.gas_stock[t]+prod[t]-m.chp.fuel_nm3[t]-m.gas_curtailment[t])
    if terminal_gas_policy=="cyclic":
        model.gas_terminal=p.Constraint(expr=model.gas_stock[n]==initial)
    model._r0_metadata.update(architecture="R2",scientific_validation=False,
                              biogas_production="exogenous_from_explicit_substrate_assumption" if substrate_t_per_day is not None else "exogenous",
                              digester_sizing=digester_capacity_m3 is not None,
                              digester_capacity_m3=digester_capacity_m3,
                              substrate_t_per_day=substrate_t_per_day,
                              auxiliary_rule="fraction_of_chp_gross" if auxiliary_fraction_chp_gross is not None else "exogenous",
                              gas_curtailment="CONTROLLED_DISCARD_NOT_PHYSICAL_LEAKAGE",
                              physical_leakage="NOT_MODELLED_NOT_ASSUMED_ZERO",
                              source_boundary="REQUIRES_DOCUMENTED_SEMANTICS")
    return model
