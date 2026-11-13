"""Unit tests for conditional R1 natural-gas accounting."""

import math

import pytest

from d28.economics.chp_fuel import natural_gas_cost


def test_known_fuel_cost():
    volumes = [0.0, 20.0 / (0.35 * 9.5), 0.0, 0.0]
    result = natural_gas_cost(volumes, 3.0)
    assert result == pytest.approx(18.045112781954888)


def test_zero_fuel_cost():
    assert natural_gas_cost([0.0, 0.0], 3.0) == 0.0


def test_zero_price():
    assert natural_gas_cost([2.0, 3.0], 0.0) == 0.0


@pytest.mark.parametrize(
    "volumes",
    [
        [],
        [-1.0],
        [1.0, float("nan")],
        [float("inf")],
    ],
)
def test_invalid_fuel_volumes(volumes):
    with pytest.raises(ValueError):
        natural_gas_cost(volumes, 3.0)


@pytest.mark.parametrize(
    "price",
    [-1.0, float("nan"), float("inf")],
)
def test_invalid_gas_price(price):
    with pytest.raises(ValueError):
        natural_gas_cost([1.0], price)
