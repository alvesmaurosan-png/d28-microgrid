#!/usr/bin/env python3
"""REV16.1: R0/E100 anual e NSGA-II, sem alterar os modulos originais."""
import argparse, csv, hashlib, json, sys, math, traceback
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"src"))
from d28.optimization.biobjective_milp_connector import ConnectorInputs
from d28.optimization.economic_dispatch_f1f2 import EnergyPrices,solve_economic
from d28.economics.f1 import Economics,present_value
from d28.optimization.annual_f1_f2_reconciled_rev09 import temporal_bill

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inputs():
    path=ROOT/"data/processed/milp_inputs/R0_inputs_E100_15min.csv"
    load=[];pv=[];months=[];start=None
    with path.open(newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            t=datetime.fromisoformat(r["interval_start_local"])
            if start is None:start=t
            load.append(float(r["load_charging_ac_kw"]))
            pv.append(float(r["pv_kw_per_kwp"]))
            months.append(t.year*100+t.month)
            if abs(float(r["dt_hours"])-.25)>1e-12:raise ValueError("dt_hours != 0.25")
    if len(load)!=35040 or len(set(months))!=12:raise ValueError("Serie anual E100 incompleta")
    return ConnectorInputs(tuple(load),tuple(pv),tuple(months),dt_hours=.25,pcc_cap_kw=2500.0),path,start

def run(design,x,cfg,annual_pkm,source,c_rate=0.55,export_grid=False):
    if design["pcs_kw"]>c_rate*design["bess_kwh"]+1e-8:
        return {"status":"INVALID_DESIGN","design":design}
    prices=EnergyPrices(grid_brl_kwh=(float(cfg.energy_tariff_brl_per_kwh),)*len(x.load_kw))
    result=solve_economic("R0",design,x,prices,solver_name="appsi_highs",
                          months=x.months,
                          demand_tariff_brl_kw_month=cfg.demand_tariff_brl_per_kw_month)
    out={"route":"R0","scenario":"E100","design":design,"status":result.get("status"),
         "solver_reason":result.get("reason"),"provenance":source,
         "approval_status":"UNHOMOLOGATED_SOURCE_VALUES","f3_excluded":True}
    if result.get("status")!="PASS":return out
    bill=temporal_bill(result["grid_kw"],prices.grid_brl_kwh,x.months,.25,cfg.demand_tariff_brl_per_kw_month)
    cap=present_value(cfg,design["pv_kw"],design["bess_kwh"],design["pcs_kw"],
                      annual_variable_bill_brl=bill["total_brl"],annual_pkm=annual_pkm)
    out.update(f2_kw=result["pilot_f2_kw"],grid_energy_kwh=result["grid_energy_kwh"],
               annual_energy_cost_brl=bill["energy_brl"],annual_demand_cost_brl=bill["demand_brl"],
               annual_energy_total_brl=bill["total_brl"],monthly_peaks_kw=bill["monthly_peaks_kw"],
               dispatch_components_brl=result["cost_components_brl"],
               present_energy_cost_brl=cap["pv_total_cost_brl"],
               present_total_cost_brl=cap["pv_total_cost_brl"],
               present_value_breakdown_brl={
                   "initial_capex":cap["initial_capex_brl"],
                   "fixed_opex":cap["annual_fixed_opex_brl"]*cap["annuity_factor"],
                   "energy_and_demand":bill["total_brl"]*cap["annuity_factor"],
                   "replacements":cap["replacement_present_value_brl"],
               },
               discounted_pkm=cap["pv_pkm"],f1_brl_per_pkm=(cap["pv_total_cost_brl"]/cap["pv_pkm"] if annual_pkm else None),
               annual_pkm=annual_pkm,checks=result["checks"],
               solver_objective_brl=result["cost_brl"],
               solver_demand_brl=result["demand_charge_brl"],
               solver_objective_type=result["objective"],
               solver_monthly_peak_kw=result["monthly_peak_kw"])
    if export_grid:
        out["grid_kw"]=result["grid_kw"]
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pv-kw",type=float,default=None)
    ap.add_argument("--bess-kwh",type=float,default=None)
    ap.add_argument("--pcs-kw",type=float,default=None)
    ap.add_argument("--annual-pkm",type=float,default=None,help="PKM anual do servico, se documentado")
    ap.add_argument("--nsga2",action="store_true",help="Executa diretamente NSGA-II com MILP anual por candidato")
    ap.add_argument("--bess-max-kwh",type=float,default=None,help="Teto exploratorio opcional; sem valor usa energia total anual como limite conservador")
    ap.add_argument("--pcs-max-kw",type=float,default=5500.)
    ap.add_argument("--c-rate",type=float,default=0.55)
    ap.add_argument("--population",type=int,default=12)
    ap.add_argument("--generations",type=int,default=3)
    a=ap.parse_args()
    if a.annual_pkm is not None and a.annual_pkm<=0:ap.error("--annual-pkm deve ser positivo")
    cfg_path=ROOT/"config/economics/r0_f1_exploratory_2026.json"
    cfg=Economics.from_json(cfg_path)
    x,path,start=inputs()
    # Um algoritmo NSGA-II requer limites finitos. Sem teto BESS definido,
    # utiliza-se um limite conservador de busca, nao um limite tecnologico homologado.
    # Sem exportacao, armazenamento maior que a energia anual da carga nao pode
    # entregar mais energia util do que toda a carga anual (limite extremamente amplo).
    # Isto nao constitui prova de otimalidade global nem substitui analise de borda.
    if a.bess_max_kwh is None:
        a.bess_max_kwh = sum(max(0.,float(v))*x.dt_hours for v in x.load_kw)
        bess_bound_source = "AUTO_ANNUAL_LOAD_ENERGY_KWH_CONSERVATIVE"
    else:
        bess_bound_source = "USER_EXPLORATORY_BOUND"
    if any(not math.isfinite(v) or v<=0 for v in
           (a.bess_max_kwh,a.pcs_max_kw,a.c_rate)):
        ap.error("Limites BESS, PCS e C-rate invalidos")

    def deficit(pv_kw):
        return max(0.,max(
            float(load)-x.pcc_cap_kw-max(0.,pv_kw*float(pu))
            for load,pu in zip(x.load_kw,x.pv_pu)
        ))

    required = deficit(float(cfg.pv_capacity_max_kwp))
    domain = {
        "pv_max_kw":float(cfg.pv_capacity_max_kwp),
        "bess_max_kwh":a.bess_max_kwh,
        "bess_bound_source":bess_bound_source,
        "pcs_max_kw":a.pcs_max_kw,
        "c_rate":a.c_rate,
        "pcc_kw":x.pcc_cap_kw,
        "minimum_required_pcs_kw":required,
        "classification":"EXPLORATORY_NOT_HOMOLOGATED"
    }
    print("DOMINIO:",json.dumps(domain),flush=True)

    if required>min(a.pcs_max_kw,a.c_rate*a.bess_max_kwh):
        raise SystemExit(
            "Dominio estruturalmente inviavel: "
            "PCS/BESS maximos insuficientes"
        )

    provenance={"series":str(path.relative_to(ROOT)),"series_sha256":sha(path),
                "economics":str(cfg_path.relative_to(ROOT)),"economics_sha256":sha(cfg_path),
                "calendar_year":start.year,"base_mestre":"data/raw/parametros/Base_Mestre_D28_PC_REV07_REV02.xlsx",
                "note":"Economics JSON tem status EXPLORATORY_NOT_HOMOLOGATED; sem homologacao implicita"}
    provenance["search_domain"]=domain
    master=ROOT/provenance["base_mestre"]
    if master.exists():provenance["base_mestre_sha256"]=sha(master)
    folder=ROOT/"results";folder.mkdir(exist_ok=True)
    if not a.nsga2:
        if None in (a.pv_kw,a.bess_kwh,a.pcs_kw):
            ap.error("Para MILP isolado informe --pv-kw, --bess-kwh e --pcs-kw; para otimização use --nsga2")
        design={"pv_kw":a.pv_kw,"bess_kwh":a.bess_kwh,"pcs_kw":a.pcs_kw}
        print("Executando MILP anual R0/E100 (35040 intervalos)...",flush=True)
        output=run(design,x,cfg,a.annual_pkm,provenance,a.c_rate,export_grid=True)
        if output["status"]=="PASS":
            grid=output.pop("grid_kw")
            if len(grid)!=len(x.load_kw):
                raise RuntimeError("Despacho PCC com comprimento incorreto")
            with path.open(newline="",encoding="utf-8-sig") as input_fp:
                input_timestamps=[r["interval_start_local"] for r in csv.DictReader(input_fp)]
            if len(input_timestamps)!=len(grid):
                raise RuntimeError("Timestamps de entrada inconsistentes")
            csv_path=folder/"D28_REV16_1_R0_E100_GRID_15MIN.csv"
            with csv_path.open("w",newline="",encoding="utf-8") as fp:
                writer=csv.writer(fp)
                writer.writerow(("interval_index","interval_start_local","month_yyyymm","grid_kw"))
                for i,(kw,month) in enumerate(zip(grid,x.months)):
                    # As datas são copiadas da série de entrada para evitar reconstrução artificial.
                    # O timestamp da linha i corresponde ao mesmo índice de entrada.
                    writer.writerow((i,input_timestamps[i],month,format(float(kw),".15g")))
            output["grid_export"]={"path":str(csv_path.relative_to(ROOT)),
                                   "sha256":sha(csv_path),"rows":len(grid)}
            output["objective_vs_bill_difference_brl"]=(
                output["solver_objective_brl"]-output["annual_energy_total_brl"])
        file=folder/"D28_REV16_1_R0_E100_ANUAL.json"
        file.write_text(json.dumps(output,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
        print(json.dumps({k:output.get(k) for k in ("status","f1_brl_per_pkm","f2_kw","annual_energy_total_brl","present_energy_cost_brl")},ensure_ascii=False),flush=True)
        print("Relatorio:",file,flush=True)
        if output["status"]!="PASS":sys.exit(2)
        return
    if a.annual_pkm is None:
        ap.error("F1 = VP(custos energeticos)/VP(PKM). Informe --annual-pkm com o PKM anual do estudo; nenhum valor sera inventado.")
    if a.population<4 or a.generations<1:
        ap.error("Populacao >=4 e geracoes >=1")
    from pymoo.core.problem import ElementwiseProblem
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.optimize import minimize
    import numpy as np
    records=[]
    cache={}
    class Problem(ElementwiseProblem):
        def __init__(self):
            super().__init__(n_var=3,n_obj=2,n_ieq_constr=1,
              xl=np.array([0.,0.,0.]),xu=np.array([cfg.pv_capacity_max_kwp,a.bess_max_kwh,a.pcs_max_kw]))
        def _evaluate(self,z,out,*args,**kwargs):
            d={"pv_kw":float(z[0]),"bess_kwh":float(z[1]),"pcs_kw":float(z[2])}
            needed=deficit(d["pv_kw"])
            available=min(d["pcs_kw"],a.c_rate*d["bess_kwh"])
            if available+1e-8<needed:
                records.append({
                    "status":"INSTANTANEOUS_INFEASIBLE",
                    "design":d,
                    "required_pcs_kw":needed,
                    "available_pcs_kw":available
                })
                out["F"]=[1e15,1e15]
                out["G"]=[max(1e-6,needed-available)]
                return
            key=tuple(round(d[k],8) for k in ("pv_kw","bess_kwh","pcs_kw"))
            if key in cache:
                r=cache[key]
            else:
                try:
                    r=run(d,x,cfg,a.annual_pkm,provenance,a.c_rate)
                except Exception as exc:
                    r={
                        "status":"EXCEPTION",
                        "design":d,
                        "exception":str(exc),
                        "traceback":traceback.format_exc()
                    }
                cache[key]=r
            records.append({k:r.get(k) for k in (
                "status","design","f1_brl_per_pkm","f2_kw",
                "solver_reason","exception","traceback"
            )})
            if r["status"]=="PASS" and r.get("f1_brl_per_pkm") is not None:
                out["F"]=[r["f1_brl_per_pkm"],r["f2_kw"]];out["G"]=[-1.]
            else:
                out["F"]=[1e15,1e15];out["G"]=[1.]
    print("Iniciando NSGA-II + MILP anual R0/E100 (cada candidato: 35040 intervalos)...",flush=True)
    res=minimize(Problem(),NSGA2(pop_size=a.population),("n_gen",a.generations),seed=42,verbose=True)
    f=folder/"D28_REV16_1_R0_E100_NSGA2.json"
    f.write_text(json.dumps({"evaluations":records,"pareto_f1_f2":res.F.tolist() if res.F is not None else [],
       "pareto_designs":res.X.tolist() if res.X is not None else [],
       "population":a.population,"generations":a.generations,"search_domain":domain,"provenance":provenance},indent=2,ensure_ascii=False),encoding="utf-8")
    print("Pareto:",f)
if __name__=="__main__":main()
