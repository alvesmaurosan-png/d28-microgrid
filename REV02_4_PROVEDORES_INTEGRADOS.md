# REV02.4 — Provedores integrados, contrato e gates

## Escopo efetivamente implementado

- `IntegratedProvidersRev024` encadeia executor MILP (injetado) e construtor econômico (injetado) em **uma única avaliação**.
- O executor deve retornar `OperationalEvidence` com `CertifiedDispatch` pós-solver, `run_id`, cenário, design e SHA-256 da série PCC.
- O construtor econômico recebe **o mesmo** `OperationalEvidence`, retorna `EconomicEvidence` com `AnnualRecord` completos e atesta a origem dos custos de energia no mesmo despacho.
- A ponte REV02.3 e o avaliador REV02.2 continuam responsáveis por F1, F2 e bloqueios.
- Não são modificados `r0_nsga2_milp.py`, `build_r0_milp`, equações Pyomo, solver ou resultados M8.

## Exemplo de integração — pseudocódigo, NÃO executável sem adaptadores reais

```python
# executor(cid, design, contract):
#   model = build_model_from_validated_D28_inputs(design, contract)
#   result = solve_once_with_highs_without_loading_infeasible(model)
#   if result.termination_condition != OPTIMAL: raise RuntimeError(...)
#   load_vars_only_after_optimal(result)
#   grid_kw = tuple(value(model.grid[t]) for t in model.T)
#   dispatch = CertifiedDispatch('optimal', grid_kw, len(grid_kw),
#                                source=f'D28:{cid}:{run_id}', timestep_hours=.25)
#   return make_operational_evidence(candidate_id=cid, scenario=contract.scenario,
#                                    design=design, run_id=run_id, dispatch=dispatch)
#
# builder(op, contract):
#   # faturamento deve ser computado da mesma série op.dispatch.import_pcc_kw
#   # + exportação, demanda contratada, tarifas e demais variáveis necessárias,
#   # conforme as equações econômicas vigentes; somente importação não basta.
#   # PKM vem da base de serviço validada, NÃO da curva de carga.
#   # retornar AnnualRecord t=0..H, custos com rubricas e proveniência completas.
#   return EconomicEvidence(op.candidate_id, op.scenario, op.run_id,
#                           op.dispatch_digest, annual_records, contract.economics_source,
#                           energy_costs_from_same_dispatch=True)
```

## Condições para execução real

1. Inspecionar a versão Windows vigente de `r0_nsga2_milp.py` e o solver corrigido.
2. Definir o modelo operacional por cenário e mapear `grid[t]`, exportação e outras variáveis exigidas pelo faturamento.
3. Implementar o faturamento e os custos da frota/infraestrutura usando a matriz reconciliada, sem criar valores.
4. Verificar equivalência dos PKM e das bases de preço (BRL constantes 2026), horizonte e taxa de desconto.
5. Executar teste sintético end-to-end com HiGHS real e custos verificáveis antes de 35.040 intervalos.

## Ressalvas

A impressão digital assegura consistência entre os dados *declarados* pelos provedores; não demonstra por si só que a série foi extraída do solver nem que o faturamento foi efetivamente calculado dela. `energy_costs_from_same_dispatch=True` é uma declaração a ser auditada na implementação real. `EVALUATED_CONDITIONAL` não é homologação.

Os 9 testes são sintéticos e usam executor injetado, sem resolver MILP. A suíte completa deve ser executada no Windows.
