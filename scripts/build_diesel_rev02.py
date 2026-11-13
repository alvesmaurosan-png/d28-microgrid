from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from d28.economics.diesel_fleet import (
    DieselAssumptions,
    export_scenarios,
)

if __name__ == "__main__":
    config_path = ROOT / "config/economics/r0_f1_exploratory_2026.json"

    with config_path.open(encoding="utf-8") as f:
        economics = json.load(f)

    rate = float(economics["discount_rate_real_year"])

    assumptions = DieselAssumptions(real_discount_rate=rate)

    output_dir = ROOT / "results/diesel_rev02"

    export_scenarios(
        ROOT / "data/processed/diesel_parameters_rev01.csv",
        output_dir,
        assumptions=assumptions,
    )

    print(
        f"Diesel REV02: E100-E450, "
        f"taxa real={rate:.2%}, "
        f"resultados em {output_dir}"
    )
