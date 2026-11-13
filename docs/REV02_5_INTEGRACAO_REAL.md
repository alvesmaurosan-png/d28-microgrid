# REV02.5 — Integração real controlada (R0)

## Limites
- O executor usa `build_r0_milp` existente e HiGHS; não altera as restrições físicas.
- O objetivo físico original do R0 continua ativo. O faturamento é calculado **após** o despacho; portanto, o despacho não é necessariamente ótimo para o custo tarifário. Uma etapa posterior deverá auditar o objetivo interno do MILP antes de declarar F1 integrada ótima.
- O faturamento simplificado cobre somente energia volumétrica e demanda mensal. Não cobre ponta/fora de ponta, impostos, bandeiras, ultrapassagem, demanda contratada ou regras regulatórias. Não usar em resultados científicos sem comprovar aderência à tarifa contratual.
- Os custos completos da frota e infraestrutura e os PKM **não são criados**. O callback `annual_economic_factory` deve retornar `AnnualRecord` completos e auditáveis; sem isso o candidato fica BLOCKED.
- R0 é PV–BESS sintético; R1–R3 e BAU/Realista/Cenários 1/2 requerem os executores específicos.

## Instalação
Extrair na raiz do repositório sem sobrescrever arquivos existentes.

```powershell
python -m pytest -q tests/test_real_milp_providers_rev02_5.py
python -m pytest -q
```

## Próximos gates obrigatórios
1. Executar teste com Pyomo/HiGHS real no Windows e conferir importação e faturamento manualmente.
2. Adaptar faturamento às tarifas reais e reconciliar com o objetivo do MILP.
3. Integrar o callback anual com custos completos e PKM comprovados, sem dupla contagem.
4. Conectar os executores físicos de R1–R3 e cenários e testar NSGA-II com casos sintéticos de ponta a ponta.
5. Somente então executar casos D28 e análise de Pareto.
