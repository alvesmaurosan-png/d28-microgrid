# D28 — Fechamento documental controlado e execução M2 (18/10/2026)

## Divergências resolvidas por harmonização textual

- AC-01: referência inicial do Tutorial alterada para PC-REV08 **proposto**, Base Mestre PC-REV07 congelada.
- AC-02: caminho canônico de figuras `src/d28/reporting/plots.py`.
- AC-03: ZIP de entradas mantido imutável; protocolo versionado separadamente no repositório.
- AC-11: exemplo histórico `reporting.py` explicitamente descontinuado; árvore de módulos canônica documentada.
- AC-09: permanece progressivo; mapa integral ID→código→teste não homologado.
- AC-10: aprovação formal do PC-REV08 **pendente**; não presumida.
- AC-12: tolerâncias científicas **pendentes**; não inventadas.

## M2 — execução real de smoke agregado R0

- Solver efetivamente executado: **HiGHS através de `scipy.optimize.milp`**.
- Status: **ótimo**, 4 intervalos artificiais.
- Importação (kW): **[100.0, 120.0, 70.0, 70.0]**.
- PV utilizada (kW): **[0.0, 30.0, 50.0, 10.0]**.
- Soma das importações: **360.0 kW** (soma de quatro potências, *não energia*; para Δt=0,25 h, 90,0 kWh).
- Verificação: balanço por intervalo, não negatividade, teto PCC, disponibilidade PV.
- Arquivo de evidência: `experiments/manifests/M2_scipy_highs_smoke.json`.

### Limitação importante

A execução **não ocorreu com Pyomo/appsi_highs**: os pacotes `pyomo` e `highspy` não estão instalados e a tentativa de instalação falhou por indisponibilidade de acesso ao índice de pacotes. O resultado confirma apenas a operacionalidade do solver HiGHS integrado ao SciPy para este LP sintético; **não valida o modelo Pyomo M2**, nem o despacho D28 completo.

## Bloqueios preservados

B01 cronologia solar×demanda; B02 recarga individual; B03 tarifa; B04 inventário ACV; B05 tecnologia/CHP; B06 anualização e PKM; B07 verificações integradas. Critério de otimização do MILP interno, tolerâncias científicas e aprovação M0 ainda requerem decisão. Nenhum resultado Pareto definitivo está autorizado.

## Próximos gates

1. Instalar `pyomo` e `highspy` em ambiente com acesso a pacotes e executar `python scripts/02_smoke_dispatch.py`.
2. Confirmar equivalência das soluções Pyomo e SciPy no smoke.
3. Registrar aprovação documental M0, sem alterar a Base Mestre.
4. Fechar B01 e B02 antes de despacho cronológico individual; demais bloqueios antes de F1/F3 e M6/M7.
