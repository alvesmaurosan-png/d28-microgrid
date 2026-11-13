# REV02.1 — Adaptador MILP → F1 integrada

## Escopo

Implementação aditiva, **sem modificação do despacho físico**, sem alteração de `r0_nsga2_milp.py` e sem simulação de preços. O adaptador recebe:

1. `CertifiedDispatch`: condição de término do MILP, série de importação PCC, quantidade esperada de intervalos e origem.
2. `AnnualRecord` de `integrated_f1_rev02.py`: custos, PKM atendidos, status de serviço, factibilidade e proveniência para `t=0..H`.
3. Cenário, taxa de desconto, horizonte e teto PCC aplicável.

O retorno contém F1 integrada e F2 efetiva somente após validações. A **origem do despacho** é um campo declarado pelo chamador, não uma verificação criptográfica. `optimal` não comprova atendimento individual das viagens; isso depende dos gates operacionais.

## Acoplamento sem mexer no MILP

Depois de resolver e carregar as variáveis de um MILP ótimo, extraia `p.value(model.grid[t])` na ordem cronológica de `model.T`. Não utilize `peak_limit_kw` como F2: F2 é o máximo da série efetiva. **Não chame o adaptador antes de carregar as variáveis**.

```python
from pyomo.environ import value
from d28.economics.milp_f1_adapter_rev02 import CertifiedDispatch, adapt_milp_to_integrated_f1

# Executar somente depois de solver ótimo, com variáveis carregadas.
# annual_records deve vir da matriz reconciliada + serviço validado;
# não derivar PKM da curva agregada de carregamento.
dispatch = CertifiedDispatch(
    termination_condition=str(term),
    import_pcc_kw=[float(value(model.grid[t])) for t in model.T],
    expected_intervals=len(model.T),
    source='run_id/cenario/ano/origem_do_modelo',
)
result = adapt_milp_to_integrated_f1(
    scenario='BAU',
    dispatch=dispatch,
    annual_cost_and_service=annual_records,
    discount_rate=taxa_homologada,
    horizon_years=20,
    pcc_cap_kw=teto_pcc_aplicavel,
)
```

## Gates não dispensados

- Ausência de custo ou PKM → `PendingEvidence`; zero só com proveniência explícita.
- Despacho não ótimo, série incompleta ou violação do PCC → `PendingEvidence`.
- O adaptador **não converte** custos históricos E100 para F1 integrada e **não gera** série de 20 anos a partir de um ano.
- O exemplo dos testes é sintético, não uma homologação.
- A restrição `expected_intervals` verifica somente comprimento, não a integridade de timestamps; a validação de calendário e origem pertence ao produtor da série.
- Para integração efetiva no NSGA-II, deve-se acrescentar posteriormente um avaliador superior que monte os registros econômicos e use os objetivos retornados, sem reutilizar `f1_present_value_brl` do M8 como F1 integrada.
