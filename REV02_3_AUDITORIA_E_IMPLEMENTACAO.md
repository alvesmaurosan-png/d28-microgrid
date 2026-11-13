# REV02.3 — Auditoria de interfaces e ponte NSGA-II

## Interfaces examinadas

1. `r0_nsga2_milp.py` (versão do arquivo no ZIP-base disponibilizado): `R0Problem._evaluate(x,out)` recebe quatro variáveis `[pv,bess,pcs_fraction,alpha]`, constrói `build_r0_milp`, acrescenta restrição de pico e objetivo econômico histórico, resolve com HiGHS, chama `evaluate_r0_model` e retorna `F=[f1_present_value_brl,f2_peak_kw]`. **Não é F1 integrada**. O ZIP-base contém interface de solver anterior à correção M8 reportada pelo usuário; portanto o arquivo não é sobrescrito neste overlay.
2. `milp_f1_adapter_rev02.py`: `CertifiedDispatch(termination_condition,import_pcc_kw,expected_intervals,source,timestep_hours)` e `adapt_milp_to_integrated_f1(...)`; exige solução ótima e série PCC completa; F2 é pico observado, não epsilon.
3. `scenario_evaluator_rev02_2.py`: `ScenarioCandidate` e `evaluate_candidate()` retornam `EVALUATED_CONDITIONAL` ou `BLOCKED`, com F1/F2 nulos quando bloqueados. `evaluate_scenario_comparison` compara os quatro cenários sob PKM anuais equivalentes.

## Implementação

`src/d28/optimization/nsga2_scenario_bridge_rev02_3.py` adiciona:

- `ScenarioContract`: contrato imutável de cenário, horizonte, taxa, PCC e fonte econômica.
- `evaluate_design_rev02_3`: recebe provedores injetados `dispatch_provider(candidate_id,design,contract)` e `economics_provider(...)`. O primeiro devolve `CertifiedDispatch` pós-MILP; o segundo devolve `Sequence[AnnualRecord]`. Não altera o modelo físico e não estima PKM.
- `nsga2_evaluation_rev02_3`: converte elegíveis em `F=[F1,F2], G=[0]`; bloqueados em `G=[1]` com placeholders **exclusivamente algorítmicos** (não científicos). A auditoria retém F1/F2 `None`.
- `make_pymoo_problem_rev02_3`: cria `ElementwiseProblem` com `n_ieq_constr=1` e histórico de auditoria; **não executa** o NSGA-II.

## Gates e limitações

- A proveniência por rubrica continua sob o contrato REV02, com status `EVALUATED_CONDITIONAL`, não homologado.
- Provedores de despacho e economia reais não são criados neste pacote. Não utilizar o `r0_nsga2_milp.py` histórico como provedor de F1 integrada.
- **Importante**: `economics_provider` deve assegurar que fluxos econômicos dependentes do despacho sejam derivados de dados operacionais certificados e não duplamente contabilizados. O contrato atual recebe design/cenário, não o despacho; a implementação real do provedor exigirá uma fonte comum de resultados certificados ou uma interface expandida, testada antes de execução real.
- `pymoo` não estava instalado no ambiente local de preparação: 9 testes passaram e 2 testes de interface pymoo foram ignorados (`skipped`). Esses dois devem executar no venv Windows do usuário, onde o M8 já utilizou pymoo.
- A suíte completa de 381 testes deve ser executada pelo usuário no próprio repositório. Esperam-se 392 testes (381 + 11), desde que o ambiente e a instalação permaneçam consistentes.

## Instalação e testes (PowerShell)

Extrair o ZIP na raiz `D28_PC_REV08_REV02` sem substituir arquivos anteriores.

```powershell
python -m pytest -q tests/test_nsga2_scenario_bridge_rev02_3.py
python -m pytest -q
```

## Próximo gate

Implementar provedores reais somente após verificar a versão efetiva de `r0_nsga2_milp.py` do Windows e reconciliar origem temporal de custos, PKM, cenários, PCC e versão dos parâmetros. Até então, apenas testes sintéticos; não executar candidatos reais D28.
