# Tutorial de desenvolvimento — Microrrede D28 · PC-REV08 REV01
## Versão final de implementação controlada · Python · PyCharm Community · GitHub · NSGA-II + MILP

**Revisão:** FINAL-REV01 (17/10/2026). **Baseline matemática vinculada:** `D28_Documento_Final_Consolidado_PC_REV07_REV02_Notacoes_Equacoes.docx`. **Status:** roteiro executável por marcos; não representa homologação R0–R3.

**Referência metodológica proposta:** PC-REV08 (aprovação formal pendente). **Base de parâmetros:** Base Mestre D28 PC-REV07, 137 IDs, congelada.  
**Arquivos fornecidos:** `D28_PACOTE_DEFINITIVO_ENTRADAS_MODELO_PC_REV07(1).zip` e `D28_Evidencias_Auditoria_REC_REV05(1).zip`.  
**Objetivo:** desenvolver, verificar e compartilhar um projeto computacional reproduzível, sem modificar hipóteses e parâmetros sem decisão documentada.

> **Atenção:** este é um tutorial de implementação, não uma declaração de homologação. B01–B04 permanecem abertos; B05–B06 parciais; B07 requer testes. A implementação agregada inicial não comprova factibilidade de recarga individual nem ACV completa.

## 1. Entender o problema antes de programar

O PC-REV07 estabelece uma arquitetura energética com rede elétrica/PCC, geração fotovoltaica, bateria estacionária (BESS), geração despachável CHP alimentada por combustível gasoso, biodigestão e armazenamento gasoso quando aplicáveis. A modelagem deve separar:

1. **Dados e cenários:** D01–D14, séries de geração e demanda, evidências e classificações.
2. **Dimensionamento:** capacidades de PV (kWp), BESS (kWh/kW), CHP (kW), biodigestão e gás, conforme alternativa selecionada.
3. **Despacho:** decisões cronológicas de importação, PV, carga/descarga BESS, CHP e combustível.
4. **Indicadores:** F1 = VPL dos custos do sistema energético / VPL dos passageiros·km (BRL/PKM; EQ-040); F2 = máximo de importação no PCC (kW; EQ-041); F3 = emissões de ciclo de vida do sistema energético / PKM (kgCO₂e/PKM; EQ-045). As fronteiras e bloqueios constam da especificação REV02.
5. **Otimização multiobjetivo:** NSGA-II propõe dimensionamentos; MILP calcula despacho factível e indicadores para cada candidato.

Cenários: E100, E200, E300 (2026), E375 (2038), E450 (2050). Frota total de 450 veículos é hipótese sintética, não medição de frota real.

## 2. Instalar as ferramentas

Instale Python 3.11 ou 3.12, PyCharm Community, Git e uma conta GitHub. Confirme em terminal:

```powershell
python --version
git --version
```

No PyCharm: **New Project → Pure Python → Location** `D28_Microrrede_Otimizacao` → **New Virtualenv**. Selecione o interpretador Python instalado. No terminal integrado:

```powershell
python -m pip install --upgrade pip
python -m pip install pandas numpy openpyxl pyyaml pyomo highspy pymoo matplotlib pytest
python -m pip freeze > requirements-lock.txt
```

**Por que essas bibliotecas?** `pandas` lê CSV; `openpyxl` lê a planilha sem alterá-la; `PyYAML` organiza configurações; `Pyomo` formula MILP; `HiGHS` resolve MILP; `pymoo` implementa NSGA-II; `pytest` verifica invariantes; `matplotlib` produz gráficos. A licença/disponibilidade do solver e a compatibilidade do Python devem ser conferidas na máquina de execução. Não utilizar `pip freeze` como substituto do arquivo de requisitos de alto nível.

Crie `requirements.txt`:

```text
numpy
pandas
openpyxl
PyYAML
pyomo
highspy
pymoo
matplotlib
pytest
```

## 3. Criar a estrutura do repositório

```text
D28_Microrrede_Otimizacao/
├── README.md
├── LICENSE                         # definir licença antes de publicar
├── .gitignore
├── requirements.txt
├── requirements-lock.txt
├── config/
│   ├── base.yaml
│   └── decisoes_metodologicas.yaml
├── data/
│   ├── raw/                        # arquivos de entrada congelados
│   └── processed/                  # derivados; não editar raw
├── docs/
│   ├── protocolo/                  # PC-REV07
│   ├── rastreabilidade/             # mapas de IDs e bloqueios
│   └── metodologia.md
├── src/d28/
│   ├── __init__.py
│   ├── paths.py
│   ├── inputs.py
│   ├── validation.py
│   ├── scenarios.py
│   ├── technologies.py
│   ├── dispatch_milp.py
│   ├── objectives.py
│   ├── optimizer_nsga2.py
│   ├── experiments.py
│   └── reporting/              # pareto.py e plots.py
├── tests/
│   ├── test_inputs.py
│   ├── test_energy_balance.py
│   ├── test_storage.py
│   └── test_objectives.py
├── scripts/
│   ├── 01_validate_inputs.py
│   ├── 02_smoke_dispatch.py
│   ├── 03_run_nsga2.py
│   └── 04_export_results.py
└── results/                       # saídas locais, não versionadas
```

Crie as pastas pelo painel Project do PyCharm ou pelo Explorer do Windows. Marque `src` como **Sources Root** ou instale o projeto em modo editável depois de criar `pyproject.toml`.

## 4. Distribuir os dois ZIPs sem duplicar a documentação

Do ZIP definitivo, extraia:

| Origem no ZIP | Destino do projeto |
|---|---|
| `01_PROTOCOLO/*.docx` | `docs/protocolo/` |
| `02_PARAMETROS/*.xlsx` | `data/raw/parametros/` |
| `03_SOLAR/*.csv` | `data/raw/solar/` |
| `04_DEMANDA/*.csv` | `data/raw/demanda/` |
| `05_INTERFACE/*.csv` | `docs/rastreabilidade/` |
| `06_INTEGRIDADE/*.json` | `docs/rastreabilidade/` |

**Não extrair o ZIP histórico inteiro dentro do projeto executável.** Mantenha-o preservado como arquivo de auditoria, separado do código e da base operacional. Consulte seu `05_codigo_historico/despacho_conjunto.py` apenas como referência histórica, nunca como implementação homologada.

Conserve nomes e hashes dos arquivos. Não edite `data/raw`. Não carregue a planilha de auditoria como se fosse uma segunda base de parâmetros.

## 5. Configuração rastreável

`config/base.yaml` (arquivo de configuração do protótipo; os campos numéricos abaixo são metadados do protocolo, não substituem os IDs da Base Mestre):

```yaml
project: D28
protocol: PC-REV08  # proposto; aprovação M0 pendente
fleet_total: 450  # hipótese sintética, não frota observada
scenarios:
  E100: {year: 2026, bev: 100}
  E200: {year: 2026, bev: 200}
  E300: {year: 2026, bev: 300}
  E375: {year: 2038, bev: 375}
  E450: {year: 2050, bev: 450}
time_step_hours: 0.25
horizon_intervals: 6720
solver: highs
model_stage: aggregate_prototype
allow_unverified_individual_charging: false
allow_full_lca_claim: false
```

`config/decisoes_metodologicas.yaml`:

```yaml
B01: {status: open, rule: positional_alignment_only}
B02: {status: open, rule: aggregated_demand_only}
B03: {status: open, rule: preserve_PC_REV07_tariffs}
B04: {status: open, rule: no_full_LCA_claim}
B05: {status: partial, rule: map_parameters_to_constraints}
B06: {status: partial, rule: no_automatic_annualization}
B07: {status: pending, rule: run_ingestion_and_solver_tests}
```

Esses arquivos **registram restrições de uso**, não aprovam novas hipóteses. Valores de potência, custos, eficiências, vida útil, emissões etc. devem ser lidos pelos IDs da Base Mestre, com validação de unidade e status. Não repetir esses números em constantes do código.

## 6. Primeira rotina funcional: leitura e auditoria dos arquivos

Crie `scripts/01_validate_inputs.py`:

```python
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARAM = ROOT / 'data/raw/parametros/Base_Mestre_D28_PC_REV07_REV02.xlsx'
SOLAR = ROOT / 'data/raw/solar/D28_solar_15min_REV12_1_3.csv'
DEMAND = ROOT / 'data/raw/demanda/D28_REV09_demanda_15min.csv'

params = pd.read_excel(PARAM, sheet_name='Parametros_137', dtype={'ID': str})
solar = pd.read_csv(SOLAR)
demand = pd.read_csv(DEMAND)

assert params['ID'].notna().all()
assert params['ID'].nunique() == 137
assert len(params) == 137
assert len(solar) == 6720
assert len(demand) == 5 * 6720
assert set(demand['scenario']) == {'E100','E200','E300','E375','E450'}

for scenario, group in demand.groupby('scenario'):
    group = group.sort_values('interval_start_min')
    assert len(group) == 6720
    assert group['interval_start_min'].tolist() == solar['interval_start_min'].tolist()
    assert ((group['energy_ac_kwh'] - 0.25 * group['power_ac_kw']).abs() < 1e-3).all()

assert (solar['interval_end_min'] - solar['interval_start_min'] == 15).all()
assert (demand['interval_end_min'] - demand['interval_start_min'] == 15).all()
print('G-D01: integridade estrutural verificada; calendário civil e recarga individual NÃO homologados.')
```

Execute no terminal:

```powershell
python scripts/01_validate_inputs.py
```

**Critério de passagem:** todos os asserts aprovados; hashes conferidos **em verificação independente do manifesto** (o script acima verifica apenas estrutura e energia, não calcula SHA-256); nenhuma transformação silenciosa de unidades. Se falhar, **interrompa**, investigue a causa e registre no RMA. O teste não resolve B01/B02.

## 7. Construir a interface de parâmetros por ID

Em `src/d28/inputs.py`, implemente `load_parameters(path)` que devolve um dicionário indexado por `ID`, preservando `Parâmetro`, `Valor REV20`, `Unidade`, `Referência consolidada PC-REV07`, status e evidência. Antes de converter valores:

1. Rejeite IDs duplicados e ausentes.
2. Distinga número, faixa, texto e parâmetro ainda não quantificado.
3. Preserve unidades originais; converta somente em funções explícitas testadas.
4. Não use `float()` em textos como “hipótese”, “a definir” ou intervalos.
5. Para cada equação, documente IDs consumidos, unidade esperada e fronteira de aplicação.
6. Não confunda `valor presente na planilha` com `valor homologado`.

Em `docs/metodologia.md`, registre uma tabela **ID → símbolo matemático → unidade → equação → fonte → status → teste**. Esta tabela é a especificação do contrato entre PC-REV07 e código.

## 8. Preparar as séries cronológicas

- Demanda: `power_ac_kw` é potência elétrica AC solicitada pelo carregamento; `energy_ac_kwh` é energia por intervalo. Não somar simultaneamente as duas grandezas no balanço.
- Solar: `pv_pu` representa geração normalizada para o intervalo; a potência PV disponível é `pv_pu[t] × capacidade_PV_kWp`, sujeito aos limites técnicos e ao tratamento de conversões já incorporadas à série.
- O fator já incorporado à série solar não pode ser aplicado uma segunda vez.
- Alinhamento por `interval_start_min` é **posicional**, não prova que o calendário civil da demanda seja 2025.
- A série solar horária de 8.760 registros e a série de 15 minutos de 6.720 registros não devem ser concatenadas ou tratadas como horizontes equivalentes.
- Não anualizar 70 dias por multiplicação automática sem uma regra de ponderação aprovada.

`scenarios.py` deve carregar um cenário de cada vez, ordenar intervalos e rejeitar lacunas/duplicatas.

## 9. Formulação matemática do MILP

Considere intervalos `t`, duração `Δt=0,25 h`, carga agregada `L_t` e PV disponível `PVavail_t`. Para um dimensionamento fixo proposto pelo NSGA-II, as variáveis operacionais podem incluir:

- `g_t ≥ 0`: importação da rede [kW].
- `pv_t ≥ 0`: geração PV utilizada [kW].
- `ch_t, dis_t ≥ 0`: carga e descarga BESS [kW].
- `soc_t`: energia armazenada [kWh].
- `chp_t ≥ 0`: potência elétrica CHP [kW].
- `fuel_t ≥ 0`: consumo de biogás/combustível [unidade definida].
- `u_t ∈ {0,1}`: modo de carga/descarga, se necessário.

**Balanço de potência**, quando não houver exportação (EQ-001 da especificação REV02):

`g_t + pv_t + dis_t + chp_t = L_t + ch_t + auxiliares_t`. Aqui `chp_t` deve ser líquido quando os auxiliares de digestão já tiverem sido deduzidos; caso contrário, use CHP bruto e registre auxiliares no consumo, nunca ambos.

**PV:** `0 ≤ pv_t ≤ PVavail_t`.

**PCC (EQ-002):** `0 ≤ g_t ≤ 2500 kW` e exportação zero. Não confundir o limite físico com a demanda contratada para faturamento.

**BESS (EQ-006–EQ-010; eficiências D07-008 e D07-009):**

`soc_(t+1) = soc_t + 0,922 × ch_t × Δt − dis_t × Δt / 0,922`. As eficiências de carga e descarga são ambas 0,922, conforme os IDs vigentes; não recalcular a partir de 0,85.

`0,10 × E_BESS × SOH_y ≤ soc_t ≤ 0,90 × E_BESS × SOH_y`. O SOH é coeficiente exógeno, sujeito à política temporal de reposição ainda pendente.

`ch_t ≤ P_BESS × u_t`; `dis_t ≤ P_BESS × (1-u_t)`.

**CHP e combustível:** representar conversão energia do gás → eletricidade com PCI e eficiência, limites de potência, estoque, produção/entrega e disponibilidade. **Não introduzir substrato gratuito, estoque ilimitado, combustível infinito ou emissões nulas**. Formular o balanço gasoso em unidades coerentes e documentadas.

**Condições de contorno:** definir SOC inicial/final e estoques de gás conforme PC-REV07. Se o protocolo não fixar um valor, não atribuí-lo silenciosamente. Exigir decisão explícita ou usar um teste sintético isolado, marcado como tal.

**Recarga individual:** nesta etapa, `L_t` é demanda agregada exógena. A solução **não demonstra** que cada ônibus respeitou chegada, partida, SOC e carregador. Não codificar falsa restrição individual.

**Alternativas:** implementar separadamente as topologias autorizadas pelo PC-REV07; não permitir que uma alternativa utilize recursos de outra sem decisão metodológica.

## 10. Implementar o MILP com Pyomo

Em `src/d28/dispatch_milp.py`, crie uma função `build_dispatch_model(inputs, capacities, parameters, configuration)` que:

1. Verifica unidades e limites dos parâmetros.
2. Cria `ConcreteModel`, conjunto `T` e `Param` para demanda/PV.
3. Define variáveis e equações anteriores.
4. Introduz os custos operacionais aprovados para o cenário e fronteira correspondente.
5. Define a função-objetivo **do subproblema de despacho** de forma explícita (p. ex., custo operacional), sem presumir equivalência automática com F1/F2/F3 globais.
6. Retorna modelo e um mapa de unidades/IDs de origem.

Execução sugerida:

```python
from pyomo.environ import SolverFactory, TerminationCondition
solver = SolverFactory('appsi_highs')
assert solver.available(), 'Solver HiGHS indisponível'
result = solver.solve(model)
assert result.solver.termination_condition == TerminationCondition.optimal
```

**Nota:** versões diferentes de Pyomo/HiGHS podem apresentar diferenças na API de resultados. Registre versões e teste a chamada. Inviabilidade é resultado válido de uma configuração, não motivo para substituir parâmetros arbitrariamente.

## 11. Validar o MILP antes de integrar o NSGA-II

Comece com **casos unitários sintéticos, explicitamente separados da D28**:

- Carga constante com rede ilimitada e sem outras tecnologias: balanço deve fechar.
- Sem PV, BESS ou CHP e PCC inferior ao pico: o modelo deve identificar inviabilidade se não houver flexibilidade.
- PV sem carga: não deve produzir energia utilizada acima da disponibilidade; verificar curtailment.
- BESS: conservação de energia, limites SOC, eficiência e ausência de carga/descarga simultâneas.
- CHP: consumo de combustível positivo quando há geração e respeito ao estoque.
- Caso infeasible: verificar retorno do solver sem crash.

Depois use **um único cenário D28**, sem otimização evolutiva. Registre status, gaps, tempos e resíduos máximos das equações. Só avance se os testes G-D01–G-D08 pertinentes estiverem documentados.

## 12. Definir o vetor de decisão do NSGA-II

O vetor `x` pode conter capacidades PV, BESS energia/potência, CHP, biodigestão e armazenamento gasoso, **somente quando esses ativos forem variáveis da alternativa modelada**. Os limites inferior/superior devem vir dos IDs da Base Mestre ou de decisões aprovadas; nunca usar limites genéricos escolhidos por conveniência.

Para cada `x`:

1. Aplicar checagens geométricas e de compatibilidade.
2. Construir e resolver o MILP para cada cenário exigido.
3. Verificar status e factibilidade.
4. Calcular F1/F2/F3 **somente conforme expressões e fronteiras formalizadas**.
5. Se houver inviabilidade, devolver uma violação de restrição explícita ao NSGA-II; não apresentar valores fictícios de objetivos.
6. Registrar entradas, versão, seed, solver, status e outputs.

O `pymoo` oferece `ElementwiseProblem` e `NSGA2`. Esqueleto **conceitual**:

```python
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

class D28Problem(ElementwiseProblem):
    def __init__(self, bounds, n_objectives, n_constraints):
        super().__init__(n_var=len(bounds), n_obj=n_objectives,
                         n_ieq_constr=n_constraints,
                         xl=[v[0] for v in bounds], xu=[v[1] for v in bounds])

    def _evaluate(self, x, out, *args, **kwargs):
        # TODO: construir candidato, executar MILP e computar F e G.
        # Não atribuir valores fictícios aos objetivos.
        raise NotImplementedError('Implementar após homologar equações e interfaces')

# Só executar minimize(...) quando _evaluate estiver implementado e testado.
```

**Não iniciar com centenas de indivíduos e 6.720 intervalos por avaliação.** Primeiro medir custo de um MILP, verificar resultados e definir orçamento experimental reprodutível. A redução de horizonte para teste não equivale a resultado científico do horizonte integral.

## 13. Funções-objetivo e emissões

Implemente em `objectives.py` uma função por objetivo, com:

- definição matemática e unidade;
- fronteira econômica/ambiental;
- denominador (quando aplicável);
- IDs de parâmetros;
- hipóteses condicionadas;
- testes de não dupla contagem.

Custos: BRL como moeda-base, horizonte econômico, taxa de desconto, CAPEX/OPEX, reposição e tarifa conforme decisões PC-REV07; USD somente em conversão comparativa documentada. Não misturar tarifa monômia da Base Mestre com A4 Verde sem selecionar explicitamente o caso.

Emissões: distinguir emissões operacionais de ACV; D11-013 e D11-017 têm uso condicionado, e D11-014/015/016/018/019 carecem de fatores ACV completos homologados. **Não substituir ausências por zero.** F3 completa permanece bloqueada enquanto não houver fronteira e fatores suficientes.

PKM: valor histórico exploratório não é automaticamente denominador final; não anualizar 70 dias sem decisão metodológica.

## 14. Experimentos e reprodutibilidade

Cada execução deve produzir:

```text
results/<run_id>/
  config_snapshot.yaml
  input_hashes.json
  environment.txt
  solver_status.csv
  candidates.csv
  dispatch_timeseries.csv
  objectives.csv
  constraints_audit.csv
  execution_log.txt
  figures/
```

Registre `git commit`, seed, população, gerações, tolerâncias do solver, gap, limite de tempo, computador e versões de bibliotecas. Compare soluções sob seeds comuns quando o protocolo exigir. Nunca publicar somente o gráfico de Pareto sem arquivos brutos e logs.

## 15. Testes automatizados

Execute:

```powershell
python -m pytest -q
```

Cobertura mínima: esquema/IDs, hashes, unidades, continuidade temporal, conservação de energia, balanço BESS, balanço combustível, limites PCC, não simultaneidade, objetivos, viabilidade/inviabilidade e determinismo dos testes. Um `pytest` verde não é homologação científica; também é necessária auditoria de fronteiras e evidências.

## 16. Git local e GitHub

Crie `.gitignore`:

```gitignore
.venv/
__pycache__/
.pytest_cache/
.idea/
*.py[cod]
results/
*.log
.env
```

**Antes de publicar**, escolha entre incluir ou não os dados de entrada no repositório. Verifique direitos de redistribuição dos documentos, fontes e planilhas; arquivos grandes ou de acesso restrito devem ficar fora do Git, com instruções para obtenção e hashes. Não publique dados pessoais ou credenciais.

No terminal do PyCharm:

```powershell
git init
git branch -M main
git add .
git commit -m "Estrutura inicial D28 PC-REV08 e validacao de entradas"
```

No GitHub, crie repositório vazio `d28-microrrede-otimizacao`. Copie a URL HTTPS real exibida pelo GitHub e execute:

```powershell
git remote add origin https://github.com/SEU_USUARIO/d28-microrrede-otimizacao.git
git push -u origin main
```

A URL acima é **modelo de comando**, não endereço existente. A autenticação deve usar o fluxo Git Credential Manager/GitHub (ou chave SSH); não inserir senha ou token no código. No PyCharm Community, o Git pode ser operado integralmente pelo terminal ou pela interface VCS disponível.

Fluxo de trabalho:

```powershell
git checkout -b feature/validacao-dados
# implementar e testar
git add .
git commit -m "Validar integridade temporal e unidades"
git push -u origin feature/validacao-dados
```

Abra um Pull Request no GitHub, revise testes e rastreabilidade, e faça merge apenas após aprovação. Use tags para marcos verificáveis (`v0.1-ingestao`, `v0.2-milp`, `v0.3-nsga2`), não para homologações ainda inexistentes.

## 17. Conteúdo obrigatório do README.md

Inclua: objetivo e limitações; referência PC-REV07; arquitetura NSGA-II/MILP; descrição dos cenários; instruções de instalação; estrutura dos dados e hashes; como executar testes e experimentos; decisões e bloqueios; solver e licenças; reprodutibilidade; citação acadêmica e responsável pelo projeto. Declare explicitamente que a D28 é um caso de estudo com hipóteses sintéticas.

## 18. Cronograma técnico por gates (não por datas arbitrárias)

**Convenção de marcos:** este tutorial adota os marcos M0–M7 da especificação REV02, para evitar duas nomenclaturas conflitantes. M0 é congelamento da especificação e do contrato de dados; a criação do projeto e o primeiro commit são atividades preparatórias de M0.

| Marco | Entrega | Critério de conclusão |
|---|---|---|
| M0 | Especificação e repositório controlados | REV02 referenciada, equações/IDs/unidades definidos, Git iniciado, pendências registradas |
| M1 | Ingestão e validação | 137 IDs únicos, SHA-256, 5 × 6.720 intervalos, esquema e unidades auditados |
| M2 | MILP agregado R0 | Balanço EQ-001, PCC EQ-002, PV EQ-003–005 e BESS EQ-006–010 verificados |
| M3 | Extensão R1/R2/R3 | CHP, combustível, digestão e gás EQ-011–021; apenas onde dados e decisões forem suficientes |
| M4 | Recarga individual | EQ-029–034, somente após resolução B02; SOC, conexão e gabinetes testados |
| M5 | Objetivos F1/F2/F3 | EQ-036–045; F3 completa apenas com ACV suficiente; anualização homologada |
| M6 | NSGA-II e validação experimental | Inviabilidade explícita, seeds, repetição, convergência e logs |
| M7 | Relato científico reproduzível | Resultados, testes, fronteiras, hashes, versões e limitações publicáveis |

## 19. Regras de parada

**Pare e documente** quando faltar unidade, limite, equação aprovada, combustível, condição inicial, custo, denominador ou fator de emissão. Não escolha valores de conveniência. Se um dado só admite estudo exploratório, registre o escopo e não promova seu resultado a conclusão científica.

## 20. Primeiro dia de trabalho: checklist operacional

- [ ] Criar projeto Python com `.venv` no PyCharm Community.
- [ ] Instalar dependências e salvar `requirements-lock.txt`.
- [ ] Criar a estrutura de pastas e copiar somente as entradas operacionais.
- [ ] Conferir manifesto SHA-256 e não modificar `data/raw`.
- [ ] Criar `base.yaml` e registro dos bloqueios.
- [ ] Executar `python scripts/01_validate_inputs.py`.
- [ ] Corrigir problemas de ambiente, **não os dados científicos**.
- [ ] Executar `pytest` (após criar testes).
- [ ] Criar primeiro commit e publicar no GitHub.
- [ ] Começar `inputs.py` e o mapeamento ID → equação.

---

### Nota de fidelidade documental

O DOCX PC-REV07 contém texto histórico PC-REV06 e adendos, além da consolidação vigente. O leitor deve conferir a seção **“PC-REV07 — CONSOLIDAÇÃO E VIGÊNCIA”**, os anexos e as decisões aprovadas antes de interpretar prescrições anteriores como comandos atuais. O tutorial oferece arquitetura e exemplos de implementação; **não declara implementadas equações ou funções-objetivo cuja especificação detalhada ainda deva ser transcrita e validada**.


## 21. Contrato definitivo entre a especificação REV02 e o código

A **fonte única da formulação matemática** é `D28_Documento_Final_Consolidado_PC_REV07_REV02_Notacoes_Equacoes.docx`. Este tutorial **não substitui nem renumera** EQ-000–EQ-046. A Seção 2 da REV02 fornece as notações; cada equação possui descrição dos termos. Ao programar, registre obrigatoriamente: `EQ-ID → símbolos e unidades → ID(s) D01–D14 → coluna/arquivo de origem → nome da constraint Pyomo → teste → status do bloqueio`.

| Subsistema | EQ-IDs da REV02 | Implementação prevista | Verificação mínima |
|---|---|---|---|
| Dimensionamento externo | EQ-000 | `optimizer_nsga2.py`, `technologies.py` | Domínios e codificação mista; x fixo no MILP |
| Rede e solar | EQ-001–005 | `dispatch_milp.py` | Resíduo nodal, 2.500 kW, exportação zero, curtailment |
| BESS | EQ-006–010 | `dispatch_milp.py` | Conservação em kWh, 0,922/0,922, SOC e exclusividade |
| CHP e biogás | EQ-011–021 | `technologies.py`, `dispatch_milp.py` | Conversão Nm³/kWh, limites e continuidade do estoque |
| Ônibus e carregadores | EQ-029–034 | `scenarios.py`, `dispatch_milp.py` | Disponibilidade, saída 95% SOC, gabinete dual 150 kW |
| Horizonte e PKM | EQ-035 | `scenarios.py`, `objectives.py` | Não anualizar 70 dias sem regra aprovada |
| Economia | EQ-036–040 | `objectives.py` | BRL2026, VPL, tarifas, substituições, PKM |
| Pico | EQ-041 | `dispatch_milp.py`, `objectives.py` | Máximo importado; política de despacho interno explícita |
| ACV | EQ-042–045 | `objectives.py` | Não somar fronteiras sobrepostas; bloquear F3 incompleta |
| Exergia | EQ-046 | `reporting.py` | Apenas análise complementar, não F4 |

**Observação:** a sequência de IDs salta de EQ-021 para EQ-029 na especificação vigente; **não criar EQ-022–028** por iniciativa de programação. A correspondência dos 137 parâmetros deve ser consultada na matriz oficial de rastreabilidade; não inferir que todo ID seja coeficiente físico.

## 22. Procedimento de implementação sem retrabalho

**Fase A — Preparação (M0/M1).** (1) Fixar a versão da especificação REV02 em `docs/metodologia/`; (2) conservar PC-REV07 e Base Mestre imutáveis; (3) criar o projeto e instalar dependências; (4) executar a validação de estrutura; (5) verificar separadamente os hashes SHA-256; (6) montar o mapa EQ-ID/ID/constraint/teste. Só avançar após registrar o resultado de cada gate.

**Fase B — Núcleo físico (M2).** Implementar primeiro R0 agregado em um único cenário e em horizonte sintético reduzido de testes. Comparar manualmente os balanços; em seguida executar os 6.720 intervalos, conservando continuidade de SOC. Não executar NSGA-II antes de um MILP unitário reproduzível. **O horizonte reduzido é teste de software, não experimento científico.**

**Fase C — Arquiteturas (M3/M4).** Acrescentar CHP, gás e biodigestão com testes próprios, respeitando R1/R2/R3 e as lacunas B05. A recarga individual é módulo distinto: não reconstruir horários de ônibus a partir de um CSV agregado sem evidência. B02 impede alegação de factibilidade por ônibus.

**Fase D — Indicadores e otimização (M5/M6).** Fixar previamente a regra de escolha do despacho MILP interno, pois custo e pico podem competir. Implementar F1, F2 e F3 em rotinas independentes com verificações de fronteira. Só ativar a otimização triobjetiva quando **todos os três objetivos forem computáveis com dados admissíveis**. Um protótipo de um ou dois objetivos deve receber denominação própria e não ser publicado como resultado triobjetivo final.

**Fase E — Publicação (M7).** Gerar manifesto com hashes das entradas, versão da REV02, commit Git, ambiente, solver, seed, tolerâncias, gaps, status, tempos e resultados brutos. A Metodologia do artigo cita EQ-IDs da REV02; o tutorial descreve como reproduzir os experimentos.

## 23. Verificação do ambiente e do solver

Após instalar as dependências, execute o teste isolado abaixo **antes de construir o modelo D28**:

```powershell
python -c "import pyomo.environ as p; s=p.SolverFactory('appsi_highs'); print('HiGHS disponível:', s.available())"
python -m pytest -q
```

Se o solver não estiver disponível, verifique as versões de `pyomo` e `highspy` e a instalação no interpretador da `.venv`; não altere equações para contornar problemas de ambiente. O script `01_validate_inputs.py` deve evoluir para gerar relatório JSON e testar hashes, continuidade, unicidade de intervalos e dados faltantes, preservando o arquivo inicial como referência de M1.

## 24. Matriz de bloqueios e permissões de uso

| Bloqueio | Consequência para implementação | Condição para resultado científico |
|---|---|---|
| B01 | Pareamento cronológico solar/demanda não homologado | Calendário e método temporal documentados |
| B02 | Apenas demanda agregada; recarga individual não comprovada | Dados por ônibus, janela, viagem e SOC auditados |
| B03 | Tarifas base e A4 Verde não podem ser misturadas | Estrutura tarifária do experimento fixada |
| B04 | Fatores ACV ausentes/condicionais | Inventário e fronteiras completos para F3 |
| B05 | Catálogo CHP e interfaces de tecnologias condicionais | Domínios e conversões fundamentados |
| B06 | PKM e anualização não homologados | Pesos e horizonte econômico reconciliados |
| B07 | Integração computacional ainda não demonstrada | Testes M1–M6 e execução reproduzível |

**Regra de mudança:** após o congelamento M0, toda modificação deve indicar causa, EQ-ID, IDs de parâmetros, testes, impacto nos resultados e aprovação. Mudanças em código não podem redefinir o protocolo silenciosamente.

## 25. Critério final de aceitação do tutorial

O tutorial está pronto para uso quando o desenvolvedor consegue reproduzir M0/M1 seguindo os comandos, localizar cada fórmula na REV02, identificar de onde vem cada parâmetro, separar testes sintéticos de resultados científicos e saber **exatamente em que bloqueio deve interromper** uma implementação. A conclusão de M0/M1 não implica que os módulos MILP/NSGA-II já existam ou que os bloqueios científicos tenham sido resolvidos.


## 26. Alinhamento normativo do tutorial ao PC-REV08

Este tutorial REV01 acompanha o **PC-REV08 proposto** e o Documento Final Consolidado REV03. Sua aplicação como norma depende da aprovação do PC-REV08. A Base Mestre PC-REV07 (137 IDs) permanece congelada; não alterar valores, equações EQ-000–EQ-046, arquitetura física, objetivos ou estados de bloqueio para acomodar gráficos. Os exemplos de comandos e arquivos abaixo são **especificações de implementação**, não comprovação de scripts já funcionais.

## 27. Pipeline de resultados e módulos novos

Adicionar ao repositório `src/d28/reporting/pareto.py`, `src/d28/reporting/plots.py`, `scripts/export_pareto.py`, `scripts/build_figures.py` e `tests/reporting/`. A ordem obrigatória é: entradas auditadas → MILP factível → avaliação NSGA-II → verificação de objetivos → seleção não dominada → exportação tabular → geração de gráficos → validação independente → liberação editorial.

A estrutura de cada execução é `results/<experiment_id>/<architecture_id>/<scenario_id>/<run_id>/`, contendo `manifest.json`, `candidates_all.csv`, `candidates_feasible.csv`, `convergence.csv`, `dispatch_timeseries.parquet`, `figures_manifest.csv`, `projections/` e `figures/{3d,projections,dispatch,comparisons}/`. `pareto_3d.csv` somente é liberado quando F3 estiver completo e validado. As figuras selecionadas para publicação são copiadas, preservando hashes e referências, para `reports/figures_publication/` e suas tabelas para `reports/tables_publication/`.

## 28. Como gerar e identificar as figuras

Por combinação admissível de R0–R3 e E100/E200/E300 (2026), E375 (2038), E450 (2050), gerar Pareto 3D F1–F2–F3 e projeções F1×F2, F1×F3, F2×F3; complementar com convergência, dimensionamentos e despacho das soluções representativas. São **até 20 combinações**, não 20 execuções automaticamente factíveis. Usar F1 em BRL/PKM, F2 em kW e F3 em kgCO₂e/PKM; não confundir ano de referência, período de despacho de 70 dias sintéticos (6720 passos de 15 minutos) e horizonte econômico de 20 anos.

Para obter a fronteira, filtrar apenas soluções factíveis com três objetivos válidos e aplicar dominância estrita de minimização em três dimensões: `a` domina `b` quando `F_i(a) <= F_i(b)` para todos os objetivos e existe `i` com `F_i(a) < F_i(b)`. Documentar tolerância e desempate; não transformar a projeção da frente triobjetiva em frente bidimensional reotimizada. Cada gráfico deve ter título, unidades, arquitetura, cenário, ano, `run_id`, situação de validação, fonte de dados, hash e commit.

## 29. Manifestos, tabelas e testes automatizados

O `manifest.json` deve conter `experiment_id`, `architecture_id`, `scenario_id`, `reference_year`, `run_id`, `seed`, `input_manifest_sha256`, `config_sha256`, `git_commit`, versões Python/Pyomo/HiGHS/NSGA-II, parâmetros experimentais, status dos bloqueios e estado da validação. `figures_manifest.csv` deve relacionar figura, caminho, tipo, arquivo-fonte, filtros, hash, script e status. Tabelas obrigatórias: matriz experimental; proveniência de parâmetros; resumo de factibilidade/convergência; soluções representativas; comparação R0–R3 e limitações.

Testes `tests/reporting/`: consistência de identificadores; objetivos finitos; filtragem de factíveis; não dominância independente; reprodução das projeções; integridade dos hashes; balanços do despacho; compatibilidade de unidades/denominadores; repetibilidade com seed; bloqueio de figuras finais quando F3 ou B02 não estiverem fechados. Não atribuir zeros a fatores ACV ausentes, especialmente D11-014/015/016/018/019.

## 30. Gates e aceite documental pré-implementação

**M0–M7 permanecem os gates vigentes.** Acrescentar aos critérios de aceite do gate de resultados a existência de artefatos tabulares, manifestos e figuras reproduzíveis, e aos gates de validação a checagem independente da fronteira e a rastreabilidade completa. A execução de um protótipo agregado não comprova recarga individual por veículo. Sem fechamento dos bloqueios aplicáveis, marcar saídas como exploratórias; não publicar fronteira F1–F2–F3 definitiva.

### Histórico de revisões do tutorial

| Revisão | Referência | Alteração |
|---|---|---|
| FINAL / PC-REV07 | PC-REV07 | Procedimento de implementação e gates |
| **REV01 / PC-REV08** | PC-REV08 proposto | Resultados, Pareto, scripts, diretórios, testes e proveniência |


## Nota de harmonização documental — 18/10/2026 (controle de mudanças)

Esta nota registra correções de referências cruzadas e **não** constitui aprovação do PC-REV08 nem modificação de parâmetros ou equações. O PC-REV08 é a referência metodológica **proposta**; a Base Mestre PC-REV07 de 137 IDs permanece congelada. Menções históricas ao PC-REV07 continuam válidas como identificação de origem. A implementação atual usa `src/d28/reporting/plots.py` e `src/d28/reporting/pareto.py`; o exemplo antigo `reporting.py` não é uma API vigente. O protótipo M2 é exclusivamente agregado, sintético e reduzido. B01–B07 e a definição de escalarização do MILP continuam abertos conforme auditoria. Tolerâncias científicas de dominância e repetibilidade exigem decisão antes de M6/M7.
