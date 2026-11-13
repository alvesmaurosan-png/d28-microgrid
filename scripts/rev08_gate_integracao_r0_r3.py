"""REV08: gate executável de integração R0–R3, sem declarar Pareto científico."""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

def build(architecture,load,pv,design,options):
    if architecture not in ("R0","R1","R2","R3"):
        raise ValueError("Arquitetura desconhecida")
    from d28.dispatch.milp import build_r0_milp
    from d28.dispatch.r1 import build_r1_milp
    from d28.dispatch.r2_r3 import build_r2_milp,build_r3_milp
    args=(load,pv,design["pv_kw"],design["bess_kwh"],design["pcs_kw"])
    common=dict(dt_hours=0.25,pcc_cap_kw=2500.,terminal_policy="cyclic")
    if architecture=="R0": return build_r0_milp(*args,**common)
    chp=dict(chp_capacity_kw=options["chp_capacity_kw"],
             electrical_efficiency=options["electrical_efficiency"],
             fuel_lhv_kwh_per_nm3=options["fuel_lhv_kwh_per_nm3"],
             availability=[1]*len(load))
    if architecture=="R1":return build_r1_milp(*args,**common,**chp)
    if architecture=="R3":return build_r3_milp(*args,**common,**chp,cgob_coverage_nm3=0.)
    if architecture=="R2":
        return build_r2_milp(*args,**common,**chp,
            production_nm3=[options["biogas_production_nm3_per_interval"]]*len(load),
            gasometer_capacity_nm3=options["gasometer_capacity_nm3"],
            initial_gas_nm3=options["initial_gas_nm3"],
            auxiliary_kw=[options["auxiliary_kw"]]*len(load))
    raise ValueError("Arquitetura desconhecida")

def solve_case(architecture,load,pv,design,options):
    import pyomo.environ as p
    model=build(architecture,load,pv,design,options)
    solver=p.SolverFactory("appsi_highs")
    if not solver.available(exception_flag=False):raise RuntimeError("HiGHS indisponível")
    solver.config.load_solution=False
    result=solver.solve(model,load_solutions=False)
    term=str(result.solver.termination_condition)
    out={"architecture":architecture,"termination":term,"feasible":False,
         "objectives":{"F1_brl_per_pkm":None,"F2_kw":None,"F3_kgco2e_per_pkm":None},
         "scientific_pareto_eligible":False}
    if result.solver.termination_condition!=p.TerminationCondition.optimal:
        out["reason"]="MILP não ótimo";return out
    model.solutions.load_from(result)
    grid=[float(p.value(model.grid[t])) for t in model.T]
    pv_kw=[float(p.value(model.pv[t])) for t in model.T]
    charge=[float(p.value(model.bess_charge[t])) for t in model.T]
    discharge=[float(p.value(model.bess_discharge[t])) for t in model.T]
    chp=[float(p.value(model.chp.power_gross_kw[t])) for t in model.T] if architecture!="R0" else [0.]*len(load)
    aux=[float(p.value(model.auxiliary_load_kw[t])) for t in model.T] if architecture=="R2" else [0.]*len(load)
    residual=max(abs(grid[i]+pv_kw[i]+discharge[i]+chp[i]-load[i]-charge[i]-aux[i]) for i in range(len(load)))
    peak=max(grid)
    out.update(feasible=residual<1e-5 and peak<=2500.+1e-5,
               energy_grid_kwh=sum(grid)*0.25,physical_peak_kw=peak,
               max_balance_residual_kw=residual,
               objective_policy="MIN_GRID_ENERGY_ONLY_NOT_TRI_OBJECTIVE",
               reason="F1/F3 não conectados; F2 físico apenas" )
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--architecture",choices=["R0","R1","R2","R3","ALL"],default="ALL")
    parser.add_argument("--intervals",type=int,default=4)
    parser.add_argument("--output",default="reports/D28_REV08_GATE_INTEGRACAO.json")
    args=parser.parse_args()
    if not 1<=args.intervals<=96:raise ValueError("Gate limitado a 1–96 intervalos, não é execução anual")
    source=ROOT/"data/processed/milp_inputs/R0_inputs_E100_15min.csv"
    with source.open(encoding="utf-8-sig",newline="") as f:
        rows=[]
        for r in csv.DictReader(f):
            rows.append(r)
            if len(rows)==args.intervals:break
    if len(rows)!=args.intervals:raise ValueError("Série insuficiente")
    load=[float(r["load_charging_ac_kw"]) for r in rows]
    pv=[float(r["pv_kw_per_kwp"]) for r in rows]
    design=dict(pv_kw=205.4806088017267,bess_kwh=28272.75736597176,pcs_kw=4996.651562474392)
    # Apenas valores de smoke explícitos; não são parâmetros homologados D28.
    options=dict(chp_capacity_kw=500.,electrical_efficiency=.35,
                 fuel_lhv_kwh_per_nm3=10.,biogas_production_nm3_per_interval=50.,
                 gasometer_capacity_nm3=1000.,initial_gas_nm3=500.,auxiliary_kw=0.)
    names=["R0","R1","R2","R3"] if args.architecture=="ALL" else [args.architecture]
    cases=[]
    for name in names:
        try:cases.append(solve_case(name,load,pv,design,options))
        except Exception as exc:
            cases.append(dict(architecture=name,feasible=False,termination="ERROR",
                              reason=str(exc),objectives={"F1_brl_per_pkm":None,"F2_kw":None,"F3_kgco2e_per_pkm":None},
                              scientific_pareto_eligible=False))
    result=dict(status="INTEGRATION_GATE_ONLY_NOT_SCIENTIFIC",scenario="E100",
                intervals=args.intervals,dt_hours=.25,
                parameters="EXPLORATORY_SMOKE_NOT_HOMOLOGATED",
                design=design,results=cases,
                next_gate="Conectar F1/F3 completos, decisão do MILP interno, e recarga individual antes do NSGA-II triobjetivo")
    target=ROOT/args.output
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if any(not r["feasible"] for r in cases):raise SystemExit(2)

if __name__=="__main__":main()
