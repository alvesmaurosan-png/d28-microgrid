"""D28 REV16.1.1: limiar BESS e NSGA-II com semente factivel."""
import argparse
import json
import math
from pathlib import Path

import rodar_d28_rev16_1 as base

ROOT = Path(__file__).resolve().parent
PV_MAX = 1908.225
BESS_MAX = 15000.0
PCS_MAX = 5500.0
C_RATE = 0.55

def preparar():
    x, serie, inicio = base.inputs()
    cfg = base.Economics.from_json(
        ROOT / "config/economics/r0_f1_exploratory_2026.json"
    )
    assert abs(x.pcc_cap_kw - 2500.0) < 1e-8
    assert abs(cfg.pv_capacity_max_kwp - PV_MAX) < 1e-6
    fonte = {
        "revision": "REV16.1.1",
        "series": str(serie),
        "series_sha256": base.sha(serie),
        "physical_model_changed": False,
        "classification": "EXPLORATORY_NOT_HOMOLOGATED",
    }
    return x, cfg, fonte

def avaliar(pv, bess, pcs, x, cfg, pkm, fonte):
    d = {
        "pv_kw": float(pv),
        "bess_kwh": float(bess),
        "pcs_kw": float(pcs),
    }
    return base.run(d, x, cfg, pkm, fonte, C_RATE)

def salvar(nome, dados):
    pasta = ROOT / "results"
    pasta.mkdir(exist_ok=True)
    destino = pasta / nome
    destino.write_text(
        json.dumps(dados, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print("RELATORIO:", destino, flush=True)

def limiar(x, cfg, pkm, fonte, iteracoes):
    inferior, superior = 10000.0, 15000.0
    registros = []

    def testar(bess):
        r = avaliar(PV_MAX, bess, PCS_MAX, x, cfg, pkm, fonte)
        status = r.get("status")
        motivo = r.get("solver_reason")
        registros.append({
            "bess_kwh": bess,
            "status": status,
            "solver_reason": motivo,
            "f1_brl_per_pkm": r.get("f1_brl_per_pkm"),
            "f2_kw": r.get("f2_kw"),
        })
        print(
            f"BESS={bess:.3f} kWh | STATUS={status} | MOTIVO={motivo}",
            flush=True,
        )
        if status == "PASS":
            return True
        if status == "FAILED" and "infeasible" in str(motivo).lower():
            return False
        raise RuntimeError(
            f"Resultado nao classificavel: {status}, {motivo}"
        )

    if testar(inferior):
        raise RuntimeError("Extremo inferior passou; intervalo invalido")
    if not testar(superior):
        raise RuntimeError("Extremo superior falhou; intervalo invalido")

    for i in range(iteracoes):
        meio = (inferior + superior) / 2
        if testar(meio):
            superior = meio
        else:
            inferior = meio
        print(
            f"ITERACAO {i+1}: "
            f"inviavel={inferior:.3f}, "
            f"viavel={superior:.3f}, "
            f"largura={superior-inferior:.3f} kWh",
            flush=True,
        )

    salvar("D28_REV16_1_1_LIMIAR_BESS.json", {
        "pv_kw": PV_MAX,
        "pcs_kw": PCS_MAX,
        "lower_infeasible_kwh": inferior,
        "upper_feasible_kwh": superior,
        "width_kwh": superior - inferior,
        "evaluations": registros,
        "provenance": fonte,
    })

def nsga2(x, cfg, pkm, fonte, pop, geracoes, seed):
    import numpy as np
    from pymoo.core.problem import ElementwiseProblem
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.optimize import minimize

    rng = np.random.default_rng(seed)
    registros = []
    cache = {}

    def deficit(pv):
        return max(
            0.0,
            max(
                carga - x.pcc_cap_kw - pv * solar
                for carga, solar in zip(x.load_kw, x.pv_pu)
            ),
        )

    # A primeira semente e a solucao comprovada como PASS.
    inicial = [[PV_MAX, BESS_MAX, PCS_MAX]]
    tentativas = 0

    while len(inicial) < pop and tentativas < 10000:
        tentativas += 1
        pv = float(rng.uniform(0.90 * PV_MAX, PV_MAX))
        bess = float(rng.uniform(13000.0, BESS_MAX))
        minimo_pcs = deficit(pv)
        maximo_pcs = min(PCS_MAX, C_RATE * bess)

        if minimo_pcs > maximo_pcs:
            continue

        pcs = float(rng.uniform(minimo_pcs, maximo_pcs))
        inicial.append([pv, bess, pcs])

    if len(inicial) != pop:
        raise RuntimeError("Falha na geracao da populacao inicial")

    class Problema(ElementwiseProblem):
        def __init__(self):
            super().__init__(
                n_var=3,
                n_obj=2,
                n_ieq_constr=1,
                xl=np.array([0.0, 0.0, 0.0]),
                xu=np.array([PV_MAX, BESS_MAX, PCS_MAX]),
            )

        def _evaluate(self, z, out, *args, **kwargs):
            pv, bess, pcs = map(float, z)
            requerido = deficit(pv)
            disponivel = min(pcs, C_RATE * bess)

            if disponivel + 1e-8 < requerido:
                registros.append({
                    "status": "INSTANTANEOUS_INFEASIBLE",
                    "design": [pv, bess, pcs],
                    "required_kw": requerido,
                    "available_kw": disponivel,
                })
                out["F"] = [1e15, 1e15]
                out["G"] = [max(1e-6, requerido - disponivel)]
                return

            chave = tuple(round(v, 8) for v in (pv, bess, pcs))
            if chave not in cache:
                cache[chave] = avaliar(
                    pv, bess, pcs, x, cfg, pkm, fonte
                )
            r = cache[chave]

            registros.append({
                "status": r.get("status"),
                "design": [pv, bess, pcs],
                "solver_reason": r.get("solver_reason"),
                "f1_brl_per_pkm": r.get("f1_brl_per_pkm"),
                "f2_kw": r.get("f2_kw"),
            })

            print(
                "AVALIACAO:", len(registros),
                "STATUS:", r.get("status"),
                "F1:", r.get("f1_brl_per_pkm"),
                "F2:", r.get("f2_kw"),
                flush=True,
            )

            f1 = r.get("f1_brl_per_pkm")
            f2 = r.get("f2_kw")

            if (
                r.get("status") == "PASS"
                and f1 is not None
                and f2 is not None
                and math.isfinite(f1)
                and math.isfinite(f2)
            ):
                out["F"] = [f1, f2]
                out["G"] = [-1.0]
            else:
                out["F"] = [1e15, 1e15]
                out["G"] = [1.0]

    resultado = minimize(
        Problema(),
        NSGA2(
            pop_size=pop,
            sampling=np.asarray(inicial, dtype=float),
            eliminate_duplicates=True,
        ),
        ("n_gen", geracoes),
        seed=seed,
        verbose=True,
    )

    salvar("D28_REV16_1_1_R0_E100_NSGA2.json", {
        "initial_population": inicial,
        "evaluations": registros,
        "pareto_f1_f2": (
            resultado.F.tolist() if resultado.F is not None else []
        ),
        "pareto_designs": (
            resultado.X.tolist() if resultado.X is not None else []
        ),
        "population": pop,
        "generations": geracoes,
        "seed": seed,
        "provenance": fonte,
    })

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annual-pkm", type=float, required=True)
    ap.add_argument("--threshold", action="store_true")
    ap.add_argument("--nsga2", action="store_true")
    ap.add_argument("--iterations", type=int, default=6)
    ap.add_argument("--population", type=int, default=12)
    ap.add_argument("--generations", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    if a.annual_pkm <= 0:
        ap.error("PKM anual deve ser positivo")
    if not (a.threshold or a.nsga2):
        ap.error("Informe --threshold ou --nsga2")
    if a.iterations < 1 or a.population < 4 or a.generations < 1:
        ap.error("Parametros de iteracao invalidos")

    x, cfg, fonte = preparar()

    if a.threshold:
        limiar(x, cfg, a.annual_pkm, fonte, a.iterations)

    if a.nsga2:
        nsga2(
            x, cfg, a.annual_pkm, fonte,
            a.population, a.generations, a.seed,
        )

if __name__ == "__main__":
    main()
