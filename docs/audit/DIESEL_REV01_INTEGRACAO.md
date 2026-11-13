# D28 — Integração da matriz diesel REV01

**Status:** calibração sintética condicionada; não homologada como dado real da D28.

## Instalação no projeto existente

Extraia o ZIP na raiz de `D28-Electric-Bus-Depot-Microgrid-Optimization`, **mesclando** pastas, sem substituir arquivos preexistentes. O pacote adiciona somente arquivos novos em `data/raw/`, `data/processed/`, `src/d28/economics/`, `scripts/`, `tests/` e `docs/audit/` (o arquivo de auditoria é opcional).

Na raiz, com a venv ativa:

```powershell
python .\scripts\build_diesel_rev01.py
python -m pytest .\tests\test_diesel_fleet_rev01.py -q
```

Arquivos de saída: `results/diesel_rev01/diesel_annual_rev01.csv`, `diesel_summary_rev01.csv` e `diesel_assumptions_rev01.json`.

## Conexão com o avaliador R0–R3

O MILP e o NSGA-II permanecem intactos. Para cada solução já avaliada, recuperar `f1_present_value_brl` (VPL da microrrede em R$), calcular ou carregar `pv_pkm_bev` do mesmo cenário e usar:

```python
from d28.economics.diesel_fleet import read_categories, calculate_scenario, combine_f1
categories = read_categories('data/processed/diesel_parameters_rev01.csv')
diesel = calculate_scenario('E100', categories)
normalized = combine_f1(diesel, microgrid_vpl_brl=72697962.19802955, bev_pkm_pv=SEU_VP_PKM_BEV)
```

**Atenção:** `SEU_VP_PKM_BEV` é um valor a validar, não fornecido pelo pacote. Não é correto publicar F1 total sem ele. O diesel fixo por cenário não muda a ordenação de F1 entre soluções do mesmo cenário; custos CHP permanecem dentro do VPL da microrrede, nunca na parcela diesel veicular.

## Premissas e pendências

- Frota total 450, cenário 100/200/300/375/450 BEV.
- Mix diesel hipotético: mini 5%, midi 10%, básico 25%, padron 40%, articulado 20%, com arredondamento e ajuste na última categoria.
- Consumos L/km com AC: 0.4010 / 0.5172 / 0.5614 / 0.6120 / 0.8102. Conferência em documento SPTrans primário pendente.
- Quilometragem operacional 5.574 km/ônibus/mês (proxy externo); 90% comercial (hipótese); ocupação 23 (hipótese).
- Diesel S10 R$7,22/L e ARLA R$3,00/L, consumo 0,04 L/L: parâmetros ilustrativos, sujeitos a confirmação.
- Taxa real 8%: **hipótese de demonstração, substituir pela taxa aprovada no PC-REV08**.
- CAPEX/OPEX/reposições/residual de infraestrutura diesel zerados provisoriamente; **não interpretá-los como inexistentes**.
- 20 anos independentes por cenário, preço constante em R$ 2026 no caso central.
- Sem alterar arquivos existentes do modelo e sem abrir F3 antes de validar LCA.

## Rastreabilidade

O XLSX REV01 original permanece imutável em `data/raw/`. O CSV em `data/processed/` é uma extração operacional controlada de premissas da planilha; qualquer alteração de parâmetros deve ser sincronizada entre os dois artefatos e registrada em revisão subsequente. O código **não lê o XLSX diretamente**: isso evita dependências adicionais e não simula sincronização automática inexistente.
