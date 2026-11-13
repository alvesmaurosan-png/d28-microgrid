import pytest

from d28.economics.integrated_f1_rev02 import AnnualRecord, COST_KEYS, SCENARIOS
from d28.economics.milp_f1_adapter_rev02 import CertifiedDispatch
from d28.optimization.scenario_evaluator_rev02_2 import (
    ScenarioCandidate, evaluate_candidate, evaluate_scenario_comparison,
)


def candidate(scenario="BAU", *, pkm=100, term="TerminationCondition.optimal",
              missing=None, discount=0.0, cap=20.0, source="SINTETICO"):
    annual = []
    for year in (0, 1):
        costs = {k: 0.0 for k in COST_KEYS}
        costs["frota_capex" if year == 0 else "energia_eletrica"] = 100.0 if year == 0 else 20.0
        if missing and year == 1:
            costs[missing] = None
        annual.append(AnnualRecord(year, 0.0 if year == 0 else pkm, costs,
                                   True, True, {k: "SINTETICO_SEM_HOMOLOGACAO" for k in COST_KEYS}))
    return ScenarioCandidate("cand_1", scenario, {"pv_kwp": 10.0},
        CertifiedDispatch(term, [10.0, 15.0, 8.0, 12.0], 4, "MILP_SINTETICO"),
        annual, discount, 1, cap, source)


def test_calculo_e_pico():
    r = evaluate_candidate(candidate())
    assert r["status"] == "EVALUATED_CONDITIONAL"
    assert r["f1_integrado_brl_per_pkm"] == pytest.approx(1.2)
    assert r["f2_peak_pcc_kw"] == 15.0


def test_inviavel_nao_produz_objetivos():
    r = evaluate_candidate(candidate(term="TerminationCondition.infeasible"))
    assert r["status"] == "BLOCKED"
    assert r["f1_integrado_brl_per_pkm"] is None and r["f2_peak_pcc_kw"] is None


def test_custo_ausente_bloqueia():
    assert evaluate_candidate(candidate(missing="combustivel_diesel"))["status"] == "BLOCKED"


def test_fonte_ausente_bloqueia():
    assert evaluate_candidate(candidate(source=""))["status"] == "BLOCKED"


def test_pico_superior_ao_cap_bloqueia():
    assert evaluate_candidate(candidate(cap=12.0))["status"] == "BLOCKED"


def test_comparacao_quatro_cenarios():
    r = evaluate_scenario_comparison([candidate(s) for s in SCENARIOS])
    assert r["status"] == "COMPARABLE_CONDITIONAL"
    assert r["homologated"] is False
    assert len(r["results"]) == 4


def test_pkm_distinto_bloqueia_comparacao():
    cs = [candidate(s) for s in SCENARIOS]
    cs[2] = candidate(SCENARIOS[2], pkm=99)
    r = evaluate_scenario_comparison(cs)
    assert r["status"] == "BLOCKED"
    assert any("PKM" in x for x in r["errors"])


def test_taxa_distinta_bloqueia():
    cs = [candidate(s) for s in SCENARIOS]
    cs[1] = candidate(SCENARIOS[1], discount=0.08)
    assert evaluate_scenario_comparison(cs)["status"] == "BLOCKED"


def test_cenario_ausente_bloqueia():
    assert evaluate_scenario_comparison([candidate("BAU")])["status"] == "BLOCKED"


def test_cenario_duplicado_bloqueia():
    cs = [candidate(s) for s in SCENARIOS] + [candidate("BAU")]
    assert evaluate_scenario_comparison(cs)["status"] == "BLOCKED"


def test_candidato_invalido_bloqueia_comparacao():
    cs = [candidate(s) for s in SCENARIOS]
    cs[0] = candidate("BAU", missing="arla")
    assert evaluate_scenario_comparison(cs)["status"] == "BLOCKED"
