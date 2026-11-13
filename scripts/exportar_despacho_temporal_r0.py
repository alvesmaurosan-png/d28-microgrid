"""Exportação auditável do despacho anual R0, sem modificar o MILP."""
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

FIELDS = ("grid_kw","pv_kw","pv_curt_kw","bess_charge_kw","bess_discharge_kw",
          "bess_energy_start_kwh","bess_energy_end_kwh")

def export_temporal(model, df, dt_hours, expected_grid_kwh, expected_peak_kw,
                    target_csv, target_json, input_file, pv_capacity_kw, tol_kwh=0.01):
    import pyomo.environ as p
    n=len(df)
    if n != len(model.T):
        raise ValueError("Tamanho de entrada diferente do horizonte do modelo")
    required=("interval_index","interval_start_local","load_charging_ac_kw","pv_kw_per_kwp")
    if any(c not in df.columns for c in required):
        raise ValueError("CSV não contém índice ou timestamp rastreável")
    target_csv=Path(target_csv); target_json=Path(target_json)
    input_file=Path(input_file)
    target_csv.parent.mkdir(parents=True,exist_ok=True)
    totals=defaultdict(float); monthly=defaultdict(lambda: {"energy_kwh":0.0,"peak_kw":0.0,"intervals":0})
    max_balance=0.0; max_pv=0.0; max_soc=0.0
    tmp=target_csv.with_suffix(".csv.tmp")
    with tmp.open("w",newline="",encoding="utf-8") as f:
        fields=["interval_index","interval_start_local","month","load_charging_ac_kw","pv_available_kw",*FIELDS,
                "balance_residual_kw","pv_residual_kw","soc_residual_kwh"]
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        prev=None
        for i, record in enumerate(df.itertuples(index=False)):
            if int(getattr(record,"interval_index")) != i:
                raise ValueError("Índice temporal não consecutivo")
            stamp=datetime.fromisoformat(str(getattr(record,"interval_start_local")))
            if prev is not None and (stamp-prev).total_seconds()!=dt_hours*3600:
                raise ValueError("Lacuna ou duplicação cronológica")
            prev=stamp
            v=lambda name,t:float(p.value(getattr(model,name)[t]))
            grid=v("grid",i); pv=v("pv",i); curt=v("pv_curt",i)
            charge=v("bess_charge",i); discharge=v("bess_discharge",i)
            e0=v("bess_energy",i);e1=v("bess_energy",i+1)
            load=float(getattr(record,"load_charging_ac_kw"))
            available=float(getattr(record,"pv_kw_per_kwp"))*pv_capacity_kw
            # Disponibilidade FV obtida diretamente do parâmetro do modelo e capacidade de projeto.
            balance=grid+pv+discharge-load-charge
            pv_residual=available-pv-curt
            # Eficiências padrão do validador A (parâmetros passados ao construtor).
            soc_residual=e1-e0-0.922*charge*dt_hours+discharge*dt_hours/0.922
            if any(not math.isfinite(x) for x in (grid,pv,curt,charge,discharge,e0,e1,balance,pv_residual,soc_residual)):
                raise ValueError("Despacho contém valor não finito")
            max_balance=max(max_balance,abs(balance))
            max_pv=max(max_pv,abs(pv_residual))
            max_soc=max(max_soc,abs(soc_residual))
            month=stamp.strftime("%Y-%m")
            monthly[month]["energy_kwh"]+=grid*dt_hours
            monthly[month]["peak_kw"]=max(monthly[month]["peak_kw"],grid)
            monthly[month]["intervals"]+=1
            totals["grid_energy_kwh"]+=grid*dt_hours
            totals["grid_peak_kw"]=max(totals["grid_peak_kw"],grid)
            writer.writerow(dict(interval_index=i,interval_start_local=stamp.isoformat(),
                month=month,load_charging_ac_kw=load,pv_available_kw=available,
                grid_kw=grid,pv_kw=pv,pv_curt_kw=curt,bess_charge_kw=charge,
                bess_discharge_kw=discharge,bess_energy_start_kwh=e0,bess_energy_end_kwh=e1,
                balance_residual_kw=balance,pv_residual_kw=pv_residual,soc_residual_kwh=soc_residual))
    if abs(totals["grid_energy_kwh"]-expected_grid_kwh)>tol_kwh:
        tmp.unlink(missing_ok=True);raise ValueError("Energia temporal diverge do resumo MILP")
    if abs(totals["grid_peak_kw"]-expected_peak_kw)>1e-5:
        tmp.unlink(missing_ok=True);raise ValueError("Pico temporal diverge do resumo MILP")
    if max(max_balance,max_pv,max_soc)>1e-5:
        tmp.unlink(missing_ok=True);raise ValueError("Resíduo físico acima da tolerância")
    if len(monthly)!=12:
        tmp.unlink(missing_ok=True);raise ValueError("Horizonte não contém 12 meses")
    tmp.replace(target_csv)
    sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest()
    report={"status":"TEMPORAL_EXPORT_VALIDATED_CONDITIONAL",
        "scenario":"E100","architecture":"R0","design":"A","intervals":n,"dt_hours":dt_hours,
        "input_sha256":sha(input_file),"series_sha256":sha(target_csv),
        "series_file":str(target_csv),"grid_energy_kwh":totals["grid_energy_kwh"],
        "grid_peak_kw":totals["grid_peak_kw"],"monthly":dict(sorted(monthly.items())),
        "max_balance_residual_kw":max_balance,"max_pv_residual_kw":max_pv,
        "max_soc_residual_kwh":max_soc,
        "monthly_peak_is_billable_demand":False,
        "tariff_period_allocation_performed":False,
        "evidence":"SYNTHETIC_COUNTERFACTUAL_NOT_HOMOLOGATED"}
    target_json.parent.mkdir(parents=True,exist_ok=True)
    target_json.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report
