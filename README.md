# D28 — Executor controlado de elegibilidade REV02

**Escopo entregue:** programa executável que lê o contrato real `config/rev02/scenarios.json`, verifica coerência da frota e cenários, enumera **48 células** (3 anos × 4 cenários × 4 arquiteturas), registra bloqueios explícitos e exporta `matriz_execucao.csv` e `resumo.json`. Não gera F1/F2 artificiais.

**Limitação material:** isto **não é o executor científico anual completo**. O executor comprovado R0 sintético permanece no repositório original e não é substituído. Os MILPs R1–R3 existentes ainda exigem integração econômica, logística e de séries, além de validação de gates.

## Instalação sem sobrescrever código

Copie `executar_matriz_rev02.py` para a raiz de `D28_MODELO_CONSOLIDADO` (ao lado de `src` e `config`). Não sobrescreva `src/d28/optimization/executar_d28_integrado.py`.

## Execução

```powershell
python .\executar_matriz_rev02.py --root . --output results\rev02_matriz_controlada
Get-Content results\rev02_matriz_controlada\resumo.json
Import-Csv results\rev02_matriz_controlada\matriz_execucao.csv -Delimiter ',' | Group-Object status
```

A matriz terá 48 células **bloqueadas por falta de integração/validação**; esse é um resultado de elegibilidade, não um resultado de otimização. `BAU` não recebe teto de 2.500 kW. A trajetória BEV de 2026/2030/2038 é referência, não demonstração de atendimento no Realista/C2.

## Condições para evoluir

1. Contrato documental REV02 aprovado; 137 parâmetros reconciliados, B01–B07 resolvidos conforme impacto.
2. Séries temporais de 15 min com calendário e integridade verificados, distinguindo proxy agregado de recarga individual.
3. Adaptadores R0–R3 com despacho físico, serviço e custos completos, com certificação de topologia CHP/gás.
4. Tarifa Grupo A, custos em BRL 2026, PKM de serviço e reforço de rede BAU com proveniência.
5. Testes de regressão R0, resíduos físicos, solver, hashes, seeds, e Pareto.

**Importante:** passar um manifesto de evidências não remove o bloqueio do adaptador; aprovação documental não executa nem valida software.
