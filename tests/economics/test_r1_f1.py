"""M3.5-D — Testes da consolidação econômica R1."""

from pathlib import Path

import pytest

from d28.economics.f1 import Economics, present_value
from d28.economics.chp_capital import chp_capital_present_value
from d28.economics.r1_f1 import r1_present_value


CONFIG = (
    Path(__file__).resolve().parents[2]
    / "config/economics/r0_f1_exploratory_2026.json"
)


def calculate(**overrides):
    cfg = Economics.from_json(CONFIG)

    parameters = dict(
        pv_kwp=100,
        bess_kwh=200,
        pcs_kw=100,
        chp_capacity_kw=100,
        chp_capex_brl_per_kw=6000,
        chp_fixed_opex_fraction_year=0.04,
        chp_overhaul_fraction=0.25,
        chp_overhaul_year=10,
        annual_grid_bill_brl=100000,
        annual_fuel_cost_brl=50000,
        annual_pkm=1000000,
    )

    parameters.update(overrides)

    return cfg, r1_present_value(cfg, **parameters)


def test_complete_r1_present_value():
    cfg, result = calculate()

    base = present_value(
        cfg, 100, 200, 100,
        annual_variable_bill_brl=100000,
        annual_pkm=1000000,
    )

    chp = chp_capital_present_value(
        capacity_kw=100,
        capex_brl_per_kw=6000,
        fixed_opex_fraction_year=0.04,
        overhaul_fraction=0.25,
        overhaul_year=10,
        discount_rate_real_year=cfg.discount_rate_real_year,
        horizon_years=cfg.horizon_years,
    )

    expected = (
        base["pv_total_cost_brl"]
        + chp["chp_capital_fixed_present_value_brl"]
        + 50000 * base["annuity_factor"]
    )

    assert result["pv_total_cost_brl"] == pytest.approx(expected)
    assert result["f1_brl_per_pkm"] == pytest.approx(
        expected / result["pv_pkm"]
    )


def test_missing_grid_bill_blocks_total():
    _, result = calculate(annual_grid_bill_brl=None)

    assert result["pv_total_cost_brl"] is None
    assert result["f1_brl_per_pkm"] is None


def test_missing_fuel_cost_blocks_total():
    _, result = calculate(annual_fuel_cost_brl=None)

    assert result["pv_total_cost_brl"] is None
    assert result["f1_brl_per_pkm"] is None


def test_missing_pkm_blocks_f1_only():
    _, result = calculate(annual_pkm=None)

    assert result["pv_total_cost_brl"] is not None
    assert result["pv_pkm"] is None
    assert result["f1_brl_per_pkm"] is None


def test_missing_both_annual_costs():
    _, result = calculate(
        annual_grid_bill_brl=None,
        annual_fuel_cost_brl=None,
        annual_pkm=None,
    )

    assert result["pv_total_cost_brl"] is None
    assert result["pv_pkm"] is None
    assert result["f1_brl_per_pkm"] is None
    assert (
        result["pv_cost_without_annual_variable_bills_brl"] > 0
    )


def test_zero_annual_costs_are_valid():
    _, result = calculate(
        annual_grid_bill_brl=0,
        annual_fuel_cost_brl=0,
    )

    assert result["pv_total_cost_brl"] == pytest.approx(
        result["pv_cost_without_annual_variable_bills_brl"]
    )


def test_zero_chp_matches_r0_components():
    cfg, result = calculate(
        chp_capacity_kw=0,
        annual_fuel_cost_brl=0,
    )

    base = present_value(
        cfg, 100, 200, 100,
        annual_variable_bill_brl=100000,
        annual_pkm=1000000,
    )

    assert result["pv_total_cost_brl"] == pytest.approx(
        base["pv_total_cost_brl"]
    )


def test_reject_negative_grid_bill():
    with pytest.raises(ValueError):
        calculate(annual_grid_bill_brl=-1)


def test_reject_negative_fuel_cost():
    with pytest.raises(ValueError):
        calculate(annual_fuel_cost_brl=-1)


def test_reject_nonfinite_annual_cost():
    with pytest.raises(ValueError):
        calculate(annual_fuel_cost_brl=float("nan"))


def test_reject_zero_pkm():
    with pytest.raises(ValueError):
        calculate(annual_pkm=0)


def test_reject_negative_chp_capacity():
    with pytest.raises(ValueError):
        calculate(chp_capacity_kw=-1)
