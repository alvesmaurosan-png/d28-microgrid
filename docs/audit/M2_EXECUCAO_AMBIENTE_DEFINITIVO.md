# M2 — Pyomo/HiGHS: instalação, comparação e aceite

**Situação neste ambiente:** instalação de `pyomo` e `highspy` tentou acessar o índice Python e falhou por indisponibilidade de DNS/rede. Não é possível afirmar execução ou equivalência Pyomo. O SciPy/HiGHS é o único backend executado aqui.

## PyCharm Community / Windows — terminal na raiz do repositório

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import pyomo.environ as p; import highspy; print('Pyomo + highspy importados'); print('appsi_highs disponível:', p.SolverFactory('appsi_highs').available(exception_flag=False))"
python scripts/02c_compare_pyomo_scipy.py
python -m pytest -q
```

Se o PowerShell bloquear a ativação, use diretamente `.venv\Scripts\python.exe` em todos os comandos, sem alterar a política global de execução. Configure o interpretador do projeto no PyCharm para `.venv\Scripts\python.exe`.

## Critérios de aceitação do smoke

- `status=PASS` no manifesto `experiments/manifests/M2_pyomo_vs_scipy.json`.
- Ambos os solvers retornam solução ótima para os **mesmos** quatro intervalos sintéticos.
- Potências da rede `[100,120,70,70] kW`, FV `[0,30,50,10] kW` e energia da rede `90 kWh` com Δt=0,25 h.
- Diferença máxima entre soluções, resíduo dos balanços e violações de limites ≤ `1e-6` em suas unidades (tolerância apenas para **teste de software**, não homologação de tolerâncias científicas).
- Salvar manifesto e saída dos testes no histórico do repositório; registrar versões de Python, Pyomo e solver.

## Limites de escopo

O M2 aqui é LP de quatro intervalos, com FV e importação; não modela BESS, CHP, frota individual, tarifas, ACV ou horizonte de 6.720 intervalos. Mesmo após PASS, **B01–B07, M0 e demais gates permanecem independentes**. A comparação de soluções individuais é válida neste caso, pois a solução ótima é unívoca dadas as restrições e os custos deste teste; em modelos com múltiplos ótimos, comparar também objetivo e factibilidade.
