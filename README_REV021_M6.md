# REV02.1 M6 — Dimensionamento CHP no NSGA-II

Overlay incremental: adiciona `src/d28/rev02/chp_nsga2.py` e
`tests/test_rev021_m6_chp_nsga2.py`. Não substitui módulos existentes.

O vetor genético é (PV kW, BESS kWh, fração PCS/BESS, CHP kW).
O PCS é decodificado como BESS × fração. Cada indivíduo é avaliado
pelo `evaluate_chp_design` (M5), que constrói e resolve o MILP com CHP.

Apenas Cenário 1 sintético. Os limites são exploratórios, não homologados.
F1 permanece proxy econômica sintética. A indisponibilidade, combustível,
SOC e PCC dependem dos contratos e entradas M5.

Instalação no diretório raiz do projeto:
```
Expand-Archive -Path "$env:USERPROFILE\\Downloads\\D28_REV02_1_M6_CHP_NSGA2_OVERLAY.zip" -DestinationPath "." -Force
python -m pytest tests/test_rev021_m6_chp_nsga2.py -v
python -m pytest -q
```

Meta: 341 testes (336 anteriores + 5 novos). A aprovação deve ser
confirmada no Windows com o ambiente .venv_rev02.
