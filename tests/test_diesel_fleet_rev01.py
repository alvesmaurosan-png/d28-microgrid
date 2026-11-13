from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from d28.economics.diesel_fleet import read_categories, calculate_scenario, combine_f1
CATEGORIES = read_categories(ROOT / "data/processed/diesel_parameters_rev01.csv")

def test_fleet_balances():
    for scenario in ("E100", "E200", "E300", "E375", "E450"):
        r = calculate_scenario(scenario, CATEGORIES)
        assert r["bev_buses"] + r["diesel_buses"] == 450
        assert sum(c["buses"] for c in r["categories"]) == r["diesel_buses"]
        assert len(r["annual"]) == 20

def test_e450_no_diesel_cost_or_pkm():
    r = calculate_scenario("E450", CATEGORIES)
    assert r["diesel_fleet_vpl_brl"] == 0
    assert r["diesel_pkm_pv"] == 0

def test_f1_combination():
    r = calculate_scenario("E100", CATEGORIES)
    f1 = combine_f1(r, microgrid_vpl_brl=100_000_000, bev_pkm_pv=1_000_000_000)
    assert abs(f1["vpl_energy_total_brl"] - 100_000_000 - r["diesel_fleet_vpl_brl"]) < 1e-5
    assert f1["f1_brl_per_pkm"] > 0
