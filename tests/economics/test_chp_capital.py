"""M3.5-C — Testes econômicos condicionados do CHP R1."""

import pytest

from d28.economics.chp_capital import chp_capital_present_value


def calculate(**overrides):
    parameters = dict(
        capacity_kw=100,
        capex_brl_per_kw=6000,
        fixed_opex_fraction_year=0.04,
        overhaul_fraction=0.25,
        overhaul_year=10,
        discount_rate_real_year=0.12,
        horizon_years=20,
    )
    parameters.update(overrides)
    return chp_capital_present_value(**parameters)


def test_capex_and_annual_opex():
    result = calculate()

    assert result["chp_capex_brl"] == pytest.approx(600000)
    assert result["chp_annual_fixed_opex_brl"] == pytest.approx(24000)
    assert result["chp_overhaul_cost_brl"] == pytest.approx(150000)


def test_present_value():
    result = calculate()

    annuity = sum(1.12 ** (-year) for year in range(1, 21))
    overhaul_pv = 150000 / 1.12 ** 10

    expected = 600000 + 24000 * annuity + overhaul_pv

    assert result["annuity_factor"] == pytest.approx(annuity)
    assert result["chp_overhaul_present_value_brl"] == pytest.approx(
        overhaul_pv
    )
    assert result["chp_capital_fixed_present_value_brl"] == pytest.approx(
        expected
    )


def test_overhaul_outside_horizon():
    result = calculate(horizon_years=9)

    assert result["chp_overhaul_present_value_brl"] == 0.0


def test_overhaul_at_horizon_boundary():
    result = calculate(horizon_years=10)

    assert result["chp_overhaul_present_value_brl"] == pytest.approx(
        150000 / 1.12 ** 10
    )


def test_zero_capacity():
    result = calculate(capacity_kw=0)

    assert result["chp_capex_brl"] == 0.0
    assert result["chp_annual_fixed_opex_brl"] == 0.0
    assert result["chp_capital_fixed_present_value_brl"] == 0.0


def test_zero_discount_rate():
    result = calculate(discount_rate_real_year=0)

    assert result["chp_capital_fixed_present_value_brl"] == pytest.approx(
        600000 + 24000 * 20 + 150000
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("capacity_kw", -1),
        ("capex_brl_per_kw", -1),
        ("fixed_opex_fraction_year", -0.1),
        ("overhaul_fraction", -0.1),
        ("discount_rate_real_year", -0.01),
        ("capacity_kw", float("nan")),
        ("capex_brl_per_kw", float("inf")),
        ("horizon_years", 0),
        ("horizon_years", 20.5),
        ("overhaul_year", 0),
        ("overhaul_year", 10.5),
    ],
)
def test_invalid_parameters(field, value):
    with pytest.raises(ValueError):
        calculate(**{field: value})
