"""REV06: consolidação temporal auditável e simulação de tarifa plana.
Não calcula faturamento regulatório nem altera REV03/REV04/REV05.
"""
import csv
import hashlib
import json
import math
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "results/r0_annual_validation/annual_A_E100_temporal_15min.csv"
VALIDATION = ROOT / "results/r0_annual_validation/annual_A_E100_temporal_validation.json"
REV04 = ROOT / "reports/D28_ECONOMIA_DESPACHO_ANUAL_REV04.json"
CONFIG = ROOT / "config/economics/r0_f1_exploratory_2026.json"
OUTPUT = ROOT / "reports/D28_FATURAMENTO_TEMPORAL_REV06.json"
MONTHLY_CSV = ROOT / "reports/D28_FATURAMENTO_TEMPORAL_MENSAL_REV06.csv"

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def close(a,b,atol=1e-4):
    return math.isclose(a,b,rel_tol=1e-10,abs_tol=atol)

def integrate(series_path, validation, rev04, config, *, require_annual=True):
    series_path=Path(series_path)
    if validation.get("status")!="TEMPORAL_EXPORT_VALIDATED_CONDITIONAL":
        raise ValueError("Série sem validação REV05")
    if validation.get("series_sha256") != sha256(series_path):
        raise ValueError("SHA-256 da série não corresponde à REV05")
    if validation.get("evidence")!="SYNTHETIC_COUNTERFACTUAL_NOT_HOMOLOGATED":
        raise ValueError("Proveniência inesperada")
    if rev04.get("case")!="R0_A_E100" or rev04.get("status")!="CONDITIONAL_EXPLORATORY_NOT_HOMOLOGATED":
        raise ValueError("REV04 incompatível")
    if config.get("status")!="EXPLORATORY_NOT_HOMOLOGATED" or config.get("currency")!="BRL_2026_real":
        raise ValueError("Configuração tarifária não é a exploratória esperada")
    dt=float(validation["dt_hours"])
    if not close(dt,0.25,atol=1e-12):
        raise ValueError("Resolução temporal diferente de 15 minutos")
    tariff=float(config["energy_tariff_brl_per_kwh"])
    demand_ref=float(config["demand_tariff_brl_per_kw_month"])
    if not all(math.isfinite(x) and x>=0 for x in (tariff,demand_ref)):
        raise ValueError("Coeficiente tarifário inválido")
    months=OrderedDict()
    previous=None
    count=0; energy=0.0; peak=0.0
    with series_path.open(newline="",encoding="utf-8") as f:
        reader=csv.DictReader(f)
        if not {"interval_index","interval_start_local","month","grid_kw"}.issubset(reader.fieldnames or []):
            raise ValueError("Colunas essenciais ausentes")
        for row in reader:
            if int(row["interval_index"]) != count:
                raise ValueError("Índice temporal descontínuo")
            stamp=datetime.fromisoformat(row["interval_start_local"])
            if previous is not None and stamp-previous!=timedelta(minutes=15):
                raise ValueError("Intervalos cronológicos descontínuos")
            previous=stamp
            month=stamp.strftime("%Y-%m")
            if row["month"]!=month:
                raise ValueError("Mês divergente do timestamp")
            grid=float(row["grid_kw"])
            if not math.isfinite(grid) or grid < -1e-7:
                raise ValueError("Importação negativa ou não finita")
            grid=max(grid,0.0)
            if month not in months:
                months[month]={"month":month,"intervals":0,"energy_kwh":0.0,"physical_peak_kw":0.0}
            rec=months[month]
            rec["intervals"]+=1
            rec["energy_kwh"]+=grid*dt
            rec["physical_peak_kw"]=max(rec["physical_peak_kw"],grid)
            energy+=grid*dt
            peak=max(peak,grid)
            count+=1
    if count!=validation["intervals"] or not close(energy,float(validation["grid_energy_kwh"]),atol=0.01):
        raise ValueError("Energia/intervalos não reconciliados com REV05")
    if not close(peak,float(validation["grid_peak_kw"]),atol=1e-5):
        raise ValueError("Pico não reconciliado com REV05")
    for month, rec in months.items():
        ref=validation["monthly"].get(month)
        if ref is None or rec["intervals"]!=ref["intervals"] or not close(rec["energy_kwh"],ref["energy_kwh"],atol=0.01) or not close(rec["physical_peak_kw"],ref["peak_kw"],atol=1e-5):
            raise ValueError("Mês divergente do relatório REV05: "+month)
    if len(months)!=len(validation["monthly"]):
        raise ValueError("Meses adicionais ou ausentes")
    if require_annual and (count!=35040 or len(months)!=12):
        raise ValueError("Horizonte anual incompleto")
    for rec in months.values():
        rec["flat_energy_cost_exploratory_brl"]=rec["energy_kwh"]*tariff
        rec["energy_by_tariff_period_kwh"]=None
        rec["billable_demand_kw"]=None
        rec["demand_charge_brl"]=None
        rec["demand_overrun_brl"]=None
        rec["contractually_demonstrated_energy_charge_brl"]=None
    flat_cost=sum(x["flat_energy_cost_exploratory_brl"] for x in months.values())
    previous_flat=rev04["F1_components"]["energy_purchase_flat_tariff_exploratory_brl_year"]
    if not close(flat_cost,float(previous_flat),atol=0.02):
        raise ValueError("Custo anual por tarifa plana diverge da REV04")
    if not close(energy,float(rev04["dispatch"]["grid_import_kwh_year"]),atol=0.01):
        raise ValueError("Energia diverge da REV04")
    return {
        "revision":"REV06_FATURAMENTO_TEMPORAL_R0",
        "case":"R0_A_E100",
        "status":"MONTHLY_PHYSICAL_RECONCILED_FLAT_TARIFF_EXPLORATORY",
        "provenance":"SYNTHETIC_COUNTERFACTUAL_NOT_HOMOLOGATED",
        "sources":{"temporal_csv":{"path":str(series_path),"sha256":sha256(series_path)},
                   "validation":"results/r0_annual_validation/annual_A_E100_temporal_validation.json",
                   "rev04":"reports/D28_ECONOMIA_DESPACHO_ANUAL_REV04.json",
                   "economic_config":"config/economics/r0_f1_exploratory_2026.json"},
        "intervals":count,"dt_hours":dt,"months":list(months.values()),
        "annual":{"grid_import_kwh":energy,"physical_peak_kw":peak,
                  "flat_energy_cost_exploratory_brl":flat_cost,
                  "tariff_period_energy_charge_brl":None,
                  "contractual_demand_charge_brl":None,
                  "demand_overrun_charge_brl":None,
                  "contractually_demonstrated_bill_brl":None},
        "exploratory_parameters":{"flat_energy_tariff_brl_per_kwh":tariff,
                                   "demand_tariff_reference_brl_per_kw_month":demand_ref,
                                   "demand_reference_used_for_billing":False},
        "F1":None,"F3":None,
        "limitations":[
            "Tarifa plana exploratória: não é faturamento contratado",
            "Sem calendário de ponta/fora de ponta comprovado: energia por posto não calculada",
            "Máximo físico mensal não equivale a demanda faturável ou contratada",
            "Sem regras de demanda, ultrapassagem, tributos e bandeiras: fatura demonstrada permanece null",
            "Sem duplicar a parcela de energia exploratória já calculada na REV04",
            "Não extrapolar cenário E100 por 20 anos",
        ],
    }

def main():
    for path in (SERIES,VALIDATION,REV04,CONFIG):
        if not path.exists():
            raise SystemExit("Arquivo necessário ausente: "+str(path))
    report=integrate(SERIES,load_json(VALIDATION),load_json(REV04),load_json(CONFIG))
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    with MONTHLY_CSV.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=["month","intervals","energy_kwh","physical_peak_kw","flat_energy_cost_exploratory_brl"])
        writer.writeheader()
        for m in report["months"]:
            writer.writerow({k:m[k] for k in writer.fieldnames})
    print("REV06:",report["status"])
    print("Intervalos:",report["intervals"],"| meses:",len(report["months"]))
    print("Energia anual (kWh):",report["annual"]["grid_import_kwh"])
    print("Pico físico anual (kW):",report["annual"]["physical_peak_kw"])
    print("Custo energia exploratório (R$/ano):",round(report["annual"]["flat_energy_cost_exploratory_brl"],2))
    print("Demanda faturável:",report["annual"]["contractual_demand_charge_brl"])
    print("Arquivos:",OUTPUT,MONTHLY_CSV)

if __name__=="__main__":
    main()
