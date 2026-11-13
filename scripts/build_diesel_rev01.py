from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from d28.economics.diesel_fleet import export_scenarios

if __name__ == "__main__":
    export_scenarios(ROOT / "data/processed/diesel_parameters_rev01.csv",
                     ROOT / "results/diesel_rev01")
    print("Diesel REV01: E100-E450, 20 anos, arquivos em results/diesel_rev01")
