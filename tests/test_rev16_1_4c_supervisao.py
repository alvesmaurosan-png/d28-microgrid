"""Testes unitarios sem MILP anual; executar na raiz com pytest."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / 'rev16_1_4' / 'busca_nsga2_r0_e100_rev16_1_4c.py'
EXECUTOR = ROOT / 'rev16_1_4' / 'executar_r0_e100_rev16_1_4.py'


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_timeout_nao_reutilizavel():
    m = load(DRIVER)
    assert not m.cache_reusable({'reason':'EXTERNAL_TIMEOUT_NOT_PROOF_OF_INFEASIBILITY'})
    assert not m.cache_reusable({'reason':'INTERNAL_TIME_LIMIT_NOT_PROOF_OF_INFEASIBILITY'})
    assert not m.cache_reusable({'reason':'EXECUTOR_ERROR'})
    assert m.cache_reusable({'reason':'PASS_EXPLORATORY_ONLY','accepted':True})


def test_pareto_com_tolerancia():
    m = load(DRIVER)
    rows = [
        {'accepted':True,'f1_brl_per_pkm':.12010856621094337,'f2_kw':861.3742872870262},
        {'accepted':True,'f1_brl_per_pkm':.10431114512294011,'f2_kw':1004.5766917731338},
        {'accepted':True,'f1_brl_per_pkm':.11468175122637193,'f2_kw':861.374287287001},
    ]
    nd = m.non_dominated(rows)
    assert len(nd)==2 and rows[0] not in nd and rows[1] in nd and rows[2] in nd


def test_prefiltro_preservado():
    m=load(EXECUTOR)
    d={'pv_kw':1908.225,'bess_kwh':24836.1992,'pcs_kw':15826.9717}
    rec=m.analytical_prefilter(d,2500,[7121.735604256],[0],2500)
    assert rec['reason']=='PCS_EXCEEDS_C_RATE'


def test_revisao_nao_altera_objetivos():
    s=(ROOT/'src/d28/optimization/economic_dispatch_f1f2.py').read_text()
    assert 'm.rev05_economic_objective=p.Objective(expr=m.rev05_operating_cost,sense=p.minimize)' in s
    assert 'm.rev16_demand_epigraph.add(m.grid[t] <= m.rev16_demand_peak[months[i]])' in s
