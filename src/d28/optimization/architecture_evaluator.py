"""Contrato de avaliação R0–R3 com funções econômicas/ACV externas auditáveis."""
from dataclasses import dataclass
import math
@dataclass(frozen=True)
class Evaluation:
    feasible:bool
    objectives:tuple|None
    reason:str
    audit:dict

def evaluate_architecture(architecture,model,*,solve,compute_f1,compute_f3,annual_pkm,life_years):
    if architecture not in ('R0','R1','R2','R3'):
        return Evaluation(False,None,'Arquitetura desconhecida',{})
    if not callable(solve) or not callable(compute_f1) or not callable(compute_f3):
        return Evaluation(False,None,'Solver/contabilidade ausente',{})
    if annual_pkm is None or life_years is None or annual_pkm<=0 or life_years<=0:
        return Evaluation(False,None,'PKM anual ou horizonte não homologado',{})
    if architecture!='R0' and not hasattr(model,'chp'):
        return Evaluation(False,None,'CHP físico ausente',{})
    if architecture=='R2' and not hasattr(model,'gas_transition'):
        return Evaluation(False,None,'Balanço do biogás ausente',{})
    if architecture=='R3' and not hasattr(model,'cgob_coverage_limit'):
        return Evaluation(False,None,'Cobertura CGOB não demonstrada',{})
    try:
        result=solve(model)
        if not result.get('optimal',False):return Evaluation(False,None,'MILP não ótimo',result)
        import pyomo.environ as p
        grid=[float(p.value(model.grid[t])) for t in model.T]
        if not grid:return Evaluation(False,None,'Horizonte vazio',result)
        f1=float(compute_f1(model,result,annual_pkm,life_years))
        f2=max(grid)
        lifecycle=float(compute_f3(model,result,annual_pkm,life_years))
        f3=lifecycle/(annual_pkm*life_years)
        if any(not math.isfinite(x) or x<0 for x in (f1,f2,f3)):
            raise ValueError('Objetivos inválidos')
        audit=dict(result,architecture=architecture,annual_pkm=annual_pkm,
                   life_years=life_years,lifecycle_kgco2e=lifecycle,
                   objective_units=['BRL/pkm','kW','kgCO2e/pkm'])
        return Evaluation(True,(f1,f2,f3),'',audit)
    except (ValueError,RuntimeError,ImportError,TypeError) as exc:
        return Evaluation(False,None,str(exc),{})

def nsga2_adapter(evaluations):
    if not evaluations or any(not e.feasible or e.objectives is None for e in evaluations):
        raise ValueError('População incompleta: NSGA-II bloqueado')
    return [list(e.objectives) for e in evaluations]


def evaluate_design_rev081(architecture, design, load_kw, pv_pu, *,
                           dispatch_options=None, f1_accountant=None,
                           f3_accountant=None, annual_pkm=None,
                           life_years=None, solver_name="appsi_highs",
                           dt_hours=0.25, pcc_cap_kw=2500.0):
    """Integra dimensionamento -> MILP R0-R3 -> F2 físico -> F1/F3 condicionais.

    `f1_accountant(model, audit)` retorna F1 BRL/pkm, já normalizado.
    `f3_accountant(model, audit)` retorna emissões de ciclo de vida kgCO2e
    totais, NÃO F3 normalizado. Sem ambas, objetivos permanecem incompletos.
    Nenhum horizonte curto é anualizado automaticamente.
    """
    import pyomo.environ as p
    from d28.dispatch.milp import build_r0_milp
    from d28.dispatch.r1 import build_r1_milp
    from d28.dispatch.r2_r3 import build_r2_milp, build_r3_milp

    audit={"architecture":architecture, "solver":solver_name,
           "intervals":len(load_kw), "dt_hours":dt_hours,
           "model_scope":"conditional_aggregate_dispatch",
           "F1_brl_per_pkm":None, "F2_kw":None,
           "F3_kgco2e_per_pkm":None,
           "scientific_pareto_eligible":False}
    if architecture not in ("R0","R1","R2","R3"):
        return Evaluation(False,None,"Arquitetura desconhecida",audit)
    if not load_kw or len(load_kw)!=len(pv_pu):
        return Evaluation(False,None,"Séries inválidas",audit)
    try:
        names=("pv_kw","bess_kwh","pcs_kw")
        values={key:float(design[key]) for key in names}
        if not all(math.isfinite(x) and x>=0 for x in values.values()):
            raise ValueError("Dimensionamento não finito/negativo")
        if values["pcs_kw"]>0.55*values["bess_kwh"]+1e-9:
            raise ValueError("PCS excede limite EQ-008")
        if not (math.isfinite(dt_hours) and dt_hours>0 and math.isfinite(pcc_cap_kw) and pcc_cap_kw>0):
            raise ValueError("Passo/PCC inválidos")
        options=dict(dispatch_options or {})
        common=dict(dt_hours=dt_hours,pcc_cap_kw=pcc_cap_kw,terminal_policy="cyclic")
        args=(load_kw,pv_pu,values["pv_kw"],values["bess_kwh"],values["pcs_kw"])
        if architecture=="R0":
            model=build_r0_milp(*args,**common)
        else:
            chp_fields=("chp_capacity_kw","electrical_efficiency","fuel_lhv_kwh_per_nm3","availability")
            missing=[k for k in chp_fields if k not in options]
            if missing:raise ValueError("Parâmetros CHP ausentes: "+", ".join(missing))
            chp={k:options[k] for k in chp_fields}
            if architecture=="R1":
                model=build_r1_milp(*args,**common,**chp)
            elif architecture=="R3":
                if "cgob_coverage_nm3" not in options:
                    raise ValueError("Cobertura CGOB deve ser explicitada em R3")
                model=build_r3_milp(*args,**common,**chp,
                                    cgob_coverage_nm3=options["cgob_coverage_nm3"])
            else:
                fields=("production_nm3","gasometer_capacity_nm3","initial_gas_nm3","auxiliary_kw")
                missing=[k for k in fields if k not in options]
                if missing:raise ValueError("Parâmetros R2 ausentes: "+", ".join(missing))
                model=build_r2_milp(*args,**common,**chp,
                                    **{k:options[k] for k in fields})
        solver=p.SolverFactory(solver_name)
        if not solver.available(exception_flag=False):
            return Evaluation(False,None,"Solver indisponível",audit)
        result=solver.solve(model,load_solutions=False)
        term=result.solver.termination_condition
        audit["termination"]=str(term)
        if term!=p.TerminationCondition.optimal:
            return Evaluation(False,None,"MILP não ótimo",audit)
        model.solutions.load_from(result)
        periods=list(model.T)
        grid=[float(p.value(model.grid[t])) for t in periods]
        pv=[float(p.value(model.pv[t])) for t in periods]
        discharge=[float(p.value(model.bess_discharge[t])) for t in periods]
        charge=[float(p.value(model.bess_charge[t])) for t in periods]
        chp=[float(p.value(model.chp.power_gross_kw[t])) for t in periods] if architecture!="R0" else [0.]*len(periods)
        aux=[float(p.value(model.auxiliary_load_kw[t])) for t in periods] if architecture=="R2" else [0.]*len(periods)
        residual=max(abs(grid[i]+pv[i]+discharge[i]+chp[i]-float(load_kw[i])-charge[i]-aux[i])
                     for i in range(len(periods)))
        peak=max(grid)
        audit.update(F2_kw=peak, grid_energy_kwh=sum(grid)*dt_hours,
                     physical_peak_kw=peak, max_balance_residual_kw=residual,
                     objective_policy="MIN_GRID_ENERGY_ONLY")
        if residual>1e-5 or peak>pcc_cap_kw+1e-5 or min(grid)<-1e-5:
            return Evaluation(False,None,"Resíduo físico/PCC inválido",audit)
        # Gate físico aprovado. Contabilidade é independente do solver e não inventada.
        if f1_accountant is None or f3_accountant is None:
            return Evaluation(False,None,"F1/F3 completos não fornecidos",audit)
        if annual_pkm is None or life_years is None or annual_pkm<=0 or life_years<=0:
            return Evaluation(False,None,"PKM/horizonte não demonstrados",audit)
        if len(periods)*dt_hours not in (8760,8784):
            return Evaluation(False,None,"F1/F3 exigem horizonte anual explícito",audit)
        audit["annual_pkm"]=annual_pkm
        audit["life_years"]=life_years
        f1=float(f1_accountant(model,audit))
        lifecycle=float(f3_accountant(model,audit))
        f3=lifecycle/(annual_pkm*life_years)
        if any(not math.isfinite(v) or v<0 for v in (f1,peak,f3)):
            raise ValueError("Objetivos não finitos/negativos")
        audit.update(F1_brl_per_pkm=f1,F3_kgco2e_per_pkm=f3,
                     lifecycle_kgco2e=lifecycle,
                     scientific_pareto_eligible=False,
                     objective_policy="MIN_GRID_ENERGY_ONLY_NOT_F1_F2_F3")
        return Evaluation(True,(f1,peak,f3),
                          "Objetivos computados; política de despacho interno não certificada",audit)
    except (ValueError,RuntimeError,TypeError,KeyError,ImportError) as exc:
        return Evaluation(False,None,str(exc),audit)
