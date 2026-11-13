"""Validação determinística de sessões individuais documentadas; não cria ônibus fictícios."""
import csv
from collections import defaultdict

def validate_sessions(path, *, dt_hours=.25, tolerance_kwh=1e-5):
    with open(path,encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    required={"block_id","charger_id","charge_start_abs_min","charge_end_abs_min",
              "energy_dc_kwh","power_dc_kw"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("CSV de sessões sem colunas obrigatórias")
    errors=[];chargers=defaultdict(list);ids=set()
    for row in rows:
        key=row["block_id"]
        if key in ids:errors.append((key,"duplicado"))
        ids.add(key)
        try:
            start=float(row["charge_start_abs_min"]);end=float(row["charge_end_abs_min"])
            energy=float(row["energy_dc_kwh"]);power=float(row["power_dc_kw"])
            if not (0<=start<end and energy>=0 and power>0):raise ValueError()
            # A potência nominal pode superar a média efetiva: apenas limite superior.
            if energy>power*(end-start)/60+tolerance_kwh:
                errors.append((key,"energia excede potência × duração"))
            chargers[row["charger_id"]].append((start,end,key))
        except (ValueError,TypeError):
            errors.append((key,"dados numéricos inválidos"))
    for charger,intervals in chargers.items():
        intervals.sort()
        for a,b in zip(intervals,intervals[1:]):
            if b[0]<a[1]-1e-8:errors.append((charger,f"sobreposição {a[2]} / {b[2]}"))
    return {"sessions":len(rows),"chargers":len(chargers),"errors":errors,
            "valid":not errors,"full_fleet_homologated":False}
