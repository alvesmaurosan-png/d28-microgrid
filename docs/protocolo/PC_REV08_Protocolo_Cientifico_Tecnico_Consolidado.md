# PC-REV08 — Protocolo Científico e Técnico Consolidado da Microrrede D28

**Versão proposta para controle documental | 18 de outubro de 2026 | Estado: CONSOLIDAÇÃO NORMATIVA PROPOSTA, sujeita a aprovação formal.**

**Objeto:** dimensionamento multiobjetivo e despacho cronológico de microrrede para garagem de ônibus elétricos D28, com geração fotovoltaica, armazenamento eletroquímico, CHP e, quando aplicável, biodigestão/biogás, e com produção científica reprodutível de resultados e fronteiras de Pareto.

**Princípio de integridade:** esta revisão consolida regras vigentes do PC-REV07, a especificação matemática REV02 e o conteúdo de resultados do adendo PC-REV07.1; **não altera nem homologa automaticamente** os 137 parâmetros da Base Mestre, não elimina B01–B07 e não atesta que modelos ou resultados foram executados.

## Sumário

1. Identificação, vigência e hierarquia documental
2. Histórico de revisões e alterações controladas
3. Objeto, fronteiras e perguntas científicas
4. Cenários, horizontes e arquiteturas
5. Base Mestre, dados, evidências e proveniência
6. Formulação matemática, notação e contratos
7. Acoplamento NSGA-II/MILP e elegibilidade
8. Fronteiras econômicas, ambientais e exergia
9. Plano experimental e comparabilidade
10–18. Resultados, Pareto, gráficos, tabelas, repositório e verificações
19. Bloqueios, gates e critérios de aceitação
20. Governança, versionamento e publicação
Anexo A. Especificação matemática detalhada e dicionário de símbolos
Anexo B. Matriz de entregáveis e verificação de publicação

## 1. Identificação, vigência e hierarquia documental

**Código:** PC-REV08. **Documento de referência:** PC-REV07 e respectivas decisões vigentes, incluindo PC-REV06.2 no que não conflitar. **Base de parâmetros:** Base Mestre D28 PC-REV07, 137 IDs, preservada sem modificação. **Suportes técnicos:** Especificação Matemática Consolidada REV02 e Tutorial D28, sem precedência para alterar dados aprovados. **Registro de evolução:** PC-REV07.1 incorporado por tema e tornado histórico após aprovação desta revisão.

**Precedência para execução:** (i) decisões expressamente aprovadas e documentadas; (ii) protocolo vigente PC-REV08 após aprovação; (iii) Base Mestre congelada para valores e unidades; (iv) contratos matemáticos deste documento; (v) registros históricos apenas para interpretação. Conflitos entre fontes não autorizam seleção discricionária: abrir decisão e bloquear a inferência afetada.

A designação **PC-REV08** é proposta editorial, e sua vigência somente começa após aprovação formal. Até então PC-REV07 continua a referência aprovada. As referências antigas dentro do Anexo A são preservadas como proveniência, não como comandos concorrentes.

## 2. Histórico de revisões e alterações controladas

| Versão | Natureza documental | Situação neste controle |
|---|---|---|
| PC-REV06.0 | Protocolo científico-computacional inicial | Histórico preservado |
| PC-REV06.1 | Consolidação metodológica, energética, ambiental e computacional | Histórico interpretativo |
| PC-REV06.2 | Consolidação paramétrica e referencial | Evidência histórica e decisões vigentes conforme PC-REV07 |
| PC-REV07 | Consolidação de vigência, 137 IDs e bloqueios | Baseline anterior preservado |
| PC-REV07.1 | Adendo sobre resultados, Pareto e repositório | Conteúdo incorporado nesta proposta |
| **PC-REV08** | **Protocolo integral, saídas científicas, rastreabilidade e aceitação** | **Proposto; aprovação pendente** |

**Escopo da alteração REV08:** organização integral em seções coerentes; incorporação do contrato de gráficos, tabelas, frentes de Pareto e arquivos; critérios de comparabilidade e aceitação; vínculo aos testes e equações. **Fora do escopo:** substituir valores, decidir B01–B07, validar fatores ausentes de ACV, declarar fronteiras calculadas ou homologar modelo.

## 3. Objeto, fronteiras e perguntas científicas

Estudar a capacidade de alternativas tecnológicas de atender integralmente à recarga elétrica de uma frota sintética em garagem de ônibus sob limite de importação no PCC, minimizando custo normalizado, pico de importação e emissões de ciclo de vida do sistema energético. O inventário energético exclui a fabricação e descarte dos ônibus, conforme fronteira explicitada no modelo. O modelo distingue dimensionamento, despacho, avaliação de objetivos e apresentação de resultados.

As análises são contrafactuais, não certificam frota real ou configuração física instalada da D28. O resultado científico exige declaração da fronteira, ano de referência, período operacional, horizonte financeiro, fonte de dados, nível de factibilidade e bloqueios.

## 4. Cenários, horizontes e arquiteturas

| Cenário | Ano de referência | Ônibus BEV sintéticos | Frota total sintética |
|---|---:|---:|---:|
| E100 | 2026 | 100 | 450 |
| E200 | 2026 | 200 | 450 |
| E300 | 2026 | 300 | 450 |
| E375 | 2038 | 375 | 450 |
| E450 | 2050 | 450 | 450 |

| Arquitetura | Componentes distintivos | Restrição de interpretação |
|---|---|---|
| R0 | Rede, PV, BESS e recarga | Protótipo agregado não comprova recarga individual |
| R1 | R0 + CHP alimentado por GN físico | Combustível e emissões do GN contabilizados |
| R2 | R0 + CHP a biogás local, biodigestor e gasômetro | Produção, estoque, substrato e emissões modelados |
| R3 | R0 + CHP com GN físico e atributo CGOB | CGOB contábil separado do gás fisicamente consumido |

A matriz principal contém **até 20 combinações arquitetura × cenário**, não 60: os anos 2026/2038/2050 já estão associados aos cenários. O horizonte cronológico de despacho, o ano de referência e o horizonte econômico de 20 anos são eixos conceituais distintos. O passo operacional é de 15 min; as séries de 70 dias/6.720 intervalos não são automaticamente anuais. Uma análise de horizonte alternativo exige `temporal_scope_id` explícito e dados admissíveis.

## 5. Base Mestre, dados, evidências e proveniência

A Base Mestre PC-REV07 com **137 IDs** é a única referência de valores e unidades congelados. O modelo deve importar parâmetros por ID, conservar estado e fonte, não converter `PENDENTE` em zero e registrar os arquivos brutos com SHA-256. Blocos D01–D14 abrangem dados, tecnologia, operação, economia e ACV. A matriz de rastreabilidade obrigatória relaciona `ID → símbolo → unidade → equação → restrição Pyomo → teste → estado`.

Preservar a distinção entre: (a) solar horária de 8.760 pontos; (b) solar de 15 min com 6.720 pontos; (c) demanda sintética de 70 dias por cenário; (d) eventual matriz de viagens/recarga individual, ainda pendente. Igualdade posicional de índices não prova correspondência civil. Os fatores solares não podem ser duplicados e a demanda agregada não pode ser somada novamente à recarga individual.

## 6. Formulação matemática, notação e contratos

O **Anexo A é parte integrante e normativa desta revisão proposta**, contendo o dicionário de símbolos, EQ-000 a EQ-046 (com lacunas de numeração histórica preservadas), unidades, definições, condições de contorno e pendências. Não renumerar identificadores EQ por estética; lacunas não autorizam criar equações inexistentes. Toda implementação deve documentar variáveis, índices, domínio, parâmetro, unidade, fronteira e teste; a explicação de símbolos segue cada equação na especificação.

O vetor externo `x` fixa capacidades e alternativas antes de cada MILP. O balanço elétrico opera em potência AC média, sem exportação e sem déficit admissível, com importação limitada a **2.500 kW**. A potência dos gabinetes duplos é **150 kW DC total por gabinete**, com até duas conexões, não 150 kW por conector simultâneo. Os fluxos de gás devem diferenciar Nm³/intervalo de Nm³/h e volumes físicos de normalizados.

## 7. Acoplamento NSGA-II/MILP e elegibilidade

O NSGA-II propõe capacidades admissíveis; o Pyomo/HiGHS resolve despacho MILP para cada candidato com `x` fixo; verificadores independentes auditam conservação, limites e status; só então as funções objetivo são calculadas. O critério escalar do MILP interno (custo, pico ou prioridade lexicográfica) permanece decisão metodológica pendente, que deve ser fixada antes de comparações. Uma solução não pode ser declarada ótima simultaneamente para três objetivos apenas porque seu despacho interno foi otimizado para um deles.

Candidatos inviáveis não recebem objetivos fictícios. Registrar causa, status, gap, tolerância, restrições violadas, parâmetros, hash e seed. Um protótipo R0 agregado é etapa de desenvolvimento e não resultado triobjetivo homologado. Não iniciar execuções definitivas com hiperparâmetros evolutivos arbitrários ou sem orçamento e repetibilidade aprovados.

## 8. Fronteiras econômicas, ambientais e exergia

- **F1 [BRL constantes 2026/PKM]:** valor presente dos custos do sistema energético dividido pelo valor presente do serviço de passageiros·km, com taxa real e horizonte coerentes; não anualizar 70 dias automaticamente.
- **F2 [kW]:** pico de importação no PCC no domínio temporal avaliado, com a convenção de despacho interno expressamente fixada.
- **F3 [kgCO₂e/PKM]:** emissões de ciclo de vida do sistema energético divididas pelo serviço na mesma fronteira temporal; não somar fatores de rede operacional e ACV total incompatíveis; não omitir fatores ausentes.
- **Exergia:** pós-processamento complementar, sem criar F4 ou misturar PCI e exergia química sem convenção.

Os fatores D11-014/015/016/018/019 permanecem pendentes para F3 completa; outras lacunas podem bloquear F1 ou comparabilidade. A moeda de cálculo é BRL2026; conversões para USD, se necessárias, são relatórios comparativos documentados, não parâmetros físicos substitutivos.

## 9. Plano experimental e comparabilidade

Definir antes da execução: `experiment_id`, cenários e arquiteturas elegíveis, `temporal_scope_id`, fronteira de serviço e de ACV, versão da Base Mestre, seed(s), população, gerações, operadores de variáveis mistas, tolerâncias, limite de tempo, tratamento de inviabilidade, função interna do MILP e normalização dos indicadores de comparação. Comparar arquiteturas sob orçamento e condições equivalentes; não atribuir causalidade exclusiva ao tempo quando mudam simultaneamente ano e proporção BEV. A análise de sensibilidade exige experimentos rotulados e não altera silenciosamente o caso-base.

## 10. Natureza e vigência dos resultados

Adendo prospectivo de especificação de saídas científicas e reprodutibilidade, sem alterar os 137 IDs, valores, arquiteturas, equações, cenários ou bloqueios B01–B07 do PC-REV07. O PC-REV07 original permanece preservado neste documento. A presente seção acrescenta requisitos obrigatórios de organização, apresentação, validação e publicação dos resultados. Não declara que resultados já foram produzidos.

## 11. Matriz de experimentos e identificação inequívoca

Executar e identificar separadamente as arquiteturas R0 (rede/PV/BESS), R1 (CHP a gás natural físico), R2 (CHP a biogás local) e R3 (CHP a gás natural físico com atributo CGOB contabilizado separadamente). Os cenários vigentes são E100, E200, E300 (ano de referência 2026), E375 (2038) e E450 (2050). A matriz primária é de até 4 × 5 = 20 combinações arquitetura–cenário, sujeitas à admissibilidade e aos bloqueios. Não tratar automaticamente 2026, 2038 e 2050 como três horizontes adicionais para cada cenário.

Cada execução deve conter scenario_id, architecture_id, reference_year, temporal_scope_id, economic_horizon_years, experiment_id, run_id e model_version. O horizonte operacional (série cronológica efetivamente modelada), o ano de referência do cenário e o horizonte econômico de 20 anos são dimensões distintas. Comparações só serão admitidas quando as bases temporal, monetária, ambiental e de mobilidade forem compatíveis.

## 12. Objetivos, unidades e elegibilidade das fronteiras

F1 = VPL dos custos do sistema energético / VPL dos passageiros·km [BRL2026/PKM]; F2 = máximo de importação no PCC no domínio temporal da avaliação [kW]; F3 = emissões de ciclo de vida do sistema energético / passageiros·km [kgCO₂e/PKM]. Todos os objetivos são minimizados. A escolha da função escalar do MILP interno e a convenção de avaliação de F2 devem ser fixadas antes da execução, conforme especificação matemática.

Fronteira de Pareto tridimensional F1–F2–F3: produzir somente quando F1, F2 e F3 estiverem completos, auditados e calculados sob a mesma fronteira e com soluções fisicamente factíveis. Enquanto B04 ou outros bloqueios relevantes persistirem, rotular resultados como “parciais/exploratórios”; permitir projeções ou fronteiras parciais F1–F2 somente quando ambos forem válidos, sem chamá-las de fronteira triobjetiva. Não preencher F3 ausente com zero, estimativa não homologada ou penalidade.

Uma solução será elegível para a frente publicada somente se satisfizer as restrições físicas, temporais e documentais do experimento, com status do solver e tolerâncias aceitos. Soluções inviáveis, não convergidas ou com indicadores incompletos permanecem em arquivos de auditoria, não na frente válida.

## 13. Conjunto mínimo de figuras por combinação admissível

FIG-P01: diagrama de dispersão 3D F1 × F2 × F3, com eixos e unidades, destaque dos pontos não dominados e legenda da arquitetura/cenário/horizonte. FIG-P02: projeção F1 × F2; FIG-P03: projeção F1 × F3; FIG-P04: projeção F2 × F3. As projeções de uma frente 3D são visualizações da frente triobjetiva e NÃO devem ser apresentadas automaticamente como frentes de Pareto ótimas no plano projetado.

FIG-P05: evolução da busca por geração (número de soluções factíveis, tamanho da frente, indicador de convergência quando homologado); FIG-P06: distribuição das variáveis de dimensionamento das soluções não dominadas, quando aplicável; FIG-P07: perfis de despacho de soluções representativas, com PCC, PV, BESS, CHP, demanda e demais fluxos pertinentes. Produzir somente gráficos cujos dados e fronteiras estejam validados.

As figuras deverão conter identificador único, título científico, unidade em cada eixo, legenda, referência temporal, identificação da arquitetura, cenário e versão do modelo, data de execução, descrição de filtros e fonte dos dados. Exportar em PNG (mínimo 300 dpi) e SVG ou PDF vetorial quando tecnicamente aplicável. Preservar código e dados geradores de cada figura.

## 14. Comparações entre arquiteturas, cenários e horizontes

Produzir painéis comparativos para um mesmo cenário e horizonte, com R0–R3 sobrepostos no espaço F1–F2–F3 e em projeções bidimensionais, mantendo escalas, unidades, limites e cores consistentes. Produzir painéis de evolução E100→E200→E300 no ano de 2026 e comparações E375/2038 e E450/2050 com ressalva explícita de que variam simultaneamente ano e eletrificação. Não inferir efeito temporal isolado quando a frota também muda.

Para comparar soluções e frentes, registrar quantidade de soluções viáveis/não dominadas, dominância, cobertura entre conjuntos e, se adotados, hipervolume e indicadores IGD/IGD+, sempre com normalização, referência, sentido de otimização e conjunto de referência documentados e constantes nas comparações. Não calcular indicadores tridimensionais com F3 incompleta. Comparações entre R0–R3 exigem fronteiras de custo e ACV equivalentes, inclusive tratamento transparente do CGOB em R3.

## 15. Esquema de dados e cadeia de proveniência

Cada ponto candidato deverá ter candidate_id estável e atributos: run_id, experiment_id, scenario_id, architecture_id, reference_year, temporal_scope_id, economic_horizon_years, seed, generation, candidate_hash, is_feasible, solver_status, mip_gap, max_constraint_residual, F1_brl_per_pkm, F2_kw, F3_kgco2e_per_pkm, F1_status, F2_status, F3_status, is_nondominated_3d, constraint_violation, objective_boundary_version e input_manifest_sha256. Indicadores não disponíveis devem ser NA com motivo explícito, jamais zero substitutivo.

Salvar todos os candidatos em candidates_all.csv (incluindo rejeitados e razões), soluções factíveis em candidates_feasible.csv, frente triobjetiva válida em pareto_3d.csv somente quando elegível, e projeções em projection_F1_F2.csv, projection_F1_F3.csv e projection_F2_F3.csv com campo projection_of_3d_front. Guardar dimensionamento em design_variables.csv, série temporal de despacho em dispatch_timeseries.parquet ou CSV, indicadores de convergência em convergence.csv e um registro figures_manifest.csv relacionando figura, script, consulta/filtro, CSV fonte e checksum.

## 16. Estrutura mandatória do repositório GitHub

Estrutura proposta (diretórios de resultados grandes podem permanecer fora do Git, com manifesto e instruções de reprodução):

```text
d28-microgrid/
  docs/protocolo/PC_REV08_Protocolo_Cientifico_Tecnico_Consolidado.docx
  docs/metodologia/
  docs/rastreabilidade/
  config/experiments/
  data/raw/
  data/processed/
  src/d28/dispatch/
  src/d28/objectives/
  src/d28/optimization/
  src/d28/reporting/pareto.py
  src/d28/reporting/plots.py
  scripts/run_experiment.py
  scripts/export_pareto.py
  scripts/build_figures.py
  tests/physics/
  tests/reporting/test_nondominance.py
  tests/reporting/test_figure_provenance.py
  experiments/manifests/
  results/<experiment_id>/<architecture_id>/<scenario_id>/<run_id>/
    manifest.json
    candidates_all.csv
    candidates_feasible.csv
    pareto_3d.csv                  # somente se F1/F2/F3 válidos
    projections/
    convergence.csv
    dispatch_timeseries.parquet
    figures/3d/
    figures/projections/
    figures/dispatch/
    figures/comparisons/
    figures_manifest.csv
  reports/figures_publication/
  reports/tables_publication/
```

O repositório deve conter os scripts de reprodução e os manifestos. O versionamento de resultados brutos volumosos exige política explícita (armazenamento externo, release ou repositório de dados), com hashes e links controlados. Não versionar automaticamente entradas protegidas, dados pessoais ou credenciais.

## 17. Pipeline e verificações obrigatórias

Pipeline: (i) validar entradas e status B01–B07; (ii) fixar arquitetura/cenário/horizonte e seed; (iii) executar NSGA-II + MILP com rastreabilidade; (iv) auditar factibilidade e funções objetivo; (v) consolidar candidatos; (vi) calcular não dominância no espaço objetivo válido, com minimização e tolerâncias documentadas; (vii) gerar tabelas e figuras exclusivamente a partir de arquivos auditados; (viii) gerar manifesto e checksums; (ix) reproduzir figuras em ambiente limpo; (x) publicar resultados com suas limitações.

Testes adicionais: T-P01 unicidade dos identificadores; T-P02 compatibilidade de unidades; T-P03 nenhuma solução inviável na frente; T-P04 algoritmo de não dominância validado por conjunto manual; T-P05 correspondência de cada ponto plotado ao CSV; T-P06 impossibilidade de frente 3D sem F3 completa; T-P07 eixos, escalas e legendas; T-P08 reprodutibilidade por seed/versões; T-P09 comparabilidade entre cenários; T-P10 preservação de todos os candidatos e logs.

## 18. Critério de congelamento e uso no artigo

A inclusão das figuras e da organização de resultados é uma extensão documental de saída, não uma homologação dos experimentos. Congelar o contrato de arquivos e figuras antes de iniciar as execuções definitivas. Na Metodologia, descrever o procedimento de obtenção das frentes e os critérios de não dominância; nos Resultados, apresentar as figuras e comparações com referências às tabelas e manifestos. Em ausência de F3 completa, não anunciar otimização triobjetiva concluída.


## 19. Bloqueios, gates e critérios de aceitação

| Bloqueio | Conteúdo | Efeito científico |
|---|---|---|
| B01 | Correspondência temporal solar/demanda | Impede inferência cronológica não reconciliada |
| B02 | Matriz de ônibus, viagens, conexão e SOC | Impede prova de recarga individual |
| B03 | Tarifa, demanda e faturamento | Impede F1 tarifário definitivo |
| B04 | Inventário ACV e fatores faltantes | Impede F3 completa e Pareto 3D definitivo |
| B05 | Domínios CHP, dinâmica biogás e armazenamento | Condiciona R1–R3 completos |
| B06 | Anualização, PKM e política temporal | Condiciona F1/F3 comparáveis |
| B07 | Solver, testes e tolerâncias | Condiciona aceite computacional |

**Gates M0–M7:** M0 especificação e rastreabilidade congeladas; M1 ingestão e hashes; M2 despacho agregado R0; M3 despacho R1–R3; M4 recarga individual após B02; M5 objetivos F1/F2/F3 somente quando admissíveis; M6 integração NSGA-II; M7 publicação científica auditada. A conclusão de um gate não homologa automaticamente gates posteriores.

**Testes mínimos T-001–T-016:** unicidade dos 137 IDs, coerência dimensional, não duplicação de demanda, balanço nodal, PCC, PV, BESS, CHP, gás, recarga dual, SOC individual, temporalidade, F1, F2, F3 e vínculo equação–parâmetro–constraint–teste. **Testes T-P01–T-P10:** IDs de resultados, unidades, factibilidade, não dominância, correspondência CSV–figura, bloqueio de 3D incompleta, legibilidade, reprodutibilidade, comparabilidade e preservação de candidatos/logs.

**Critério de aprovação da revisão:** texto integral e referências cruzadas revisados; nenhuma alteração inadvertida dos 137 IDs; dicionário e equações consistentes; política de resultados e figuras versionada; bloqueios identificados; decisão formal de aprovação registrada. **Critério de aprovação de resultados:** execução admissível, indicadores completos para a modalidade declarada, verificações aprovadas e reprodução independente documentada.

## 20. Governança, versionamento e publicação

O repositório GitHub deve manter histórico de commits, tags por gate, arquivo de decisões, manifestos de execução, hashes de entradas, versões de bibliotecas, configuração do solver e scripts que geram tabelas/figuras. Arquivos protegidos e dados pessoais não serão publicados sem autorização. O protocolo, a Base Mestre e o Anexo A não podem ser alterados por um script de experimento. Toda alteração após aprovação requer ID da decisão, motivo, impacto sobre equações/IDs/testes/resultados e autorização explícita.

O artigo deve separar **Metodologia** (modelo, fronteiras, algoritmos, testes e construção das frentes), **Resultados** (tabelas e gráficos identificados), **Discussão** (trade-offs, limitações e comparabilidade) e **Reprodutibilidade** (versões, hashes, repositório e disponibilidade). Não anunciar fronteiras 3D finais sem F3 completa.

## Anexo A — Especificação matemática e dicionário de notações (parte integrante)

> Texto técnico consolidado da Especificação Matemática REV02, incorporado para autossuficiência. Identificadores históricos EQ mantidos. Eventuais remissões internas a PC-REV07 significam origem da decisão, não vigência concorrente.

## A.1. Escopo científico, arquiteturas e regras de precedência

O problema possui uma camada externa de **dimensionamento multiobjetivo NSGA-II** e um subproblema interno de **despacho MILP de passo 15 min**. As arquiteturas são R0 (rede/PV/BESS), R1 (CHP com GN físico), R2 (CHP com biogás local e biodigestão) e R3 (CHP com GN físico e atributo CGOB separado). A recarga integral dos ônibus é obrigatória; a importação no PCC é limitada a 2.500 kW e a exportação é nula. Os cenários são E100, E200, E300 em 2026, E375 em 2038 e E450 em 2050. Frota total 450 é **hipótese sintética**.

**Precedência:** (1) decisão vigente do PC-REV07; (2) valor e unidade da Base Mestre congelada; (3) evidência histórica para interpretação, sem sobrescrita; (4) este documento para definição de equações e verificações. Em caso de conflito, bloquear a avaliação correspondente e registrar decisão; não selecionar valores por conveniência.

**Dois níveis de execução:** - **R0-A, agregado, desenvolvimento:** pode testar balanços, PV/BESS, importação e F2 no horizonte de 70 dias; não demonstra factibilidade individual de recarga, custo anual F1 nem ACV completa F3. - **R0-I/R1-I/R2-I/R3-I, completos:** requerem B01–B06 resolvidos nas partes pertinentes e validação B07. Não converter teste exploratório em resultado científico homologado.

## A.2. Notação, conjuntos, índices e unidades

| Símbolo                 | Definição                                     | Unidade                            |
|-------------------------|-----------------------------------------------|------------------------------------|
| `s∈S`                   | Cenário E100/E200/E300/E375/E450              | —                                  |
| `r∈R`                   | Arquitetura R0/R1/R2/R3                       | —                                  |
| `h∈H_s`                 | Intervalo cronológico efetivo do cenário      | —                                  |
| `b∈B_s`                 | Ônibus individual sintético, somente após B02 | —                                  |
| `g∈G`                   | Gabinete de recarga dual                      | —                                  |
| `y∈Y`                   | Ano do fluxo econômico; `y=0,...,20`          | ano                                |
| `m∈M_y`                 | Mês tarifário de um ano representado          | mês                                |
| `Δt`                    | Passo operacional, 15 min                     | 0,25 h                             |
| `P`                     | Potência média no intervalo                   | kW (AC ou DC indicado)             |
| `E`                     | Energia/estoque elétrico                      | kWh                                |
| `C_PV`                  | Capacidade fotovoltaica DC instalada          | kWp                                |
| `E_B`, `P_PCS`          | Capacidade nominal BESS e potência PCS        | kWh; kW                            |
| `P_CHP`                 | Potência nominal elétrica bruta CHP           | kWe                                |
| `V_BG`, `V_GN`, `V_CH4` | Volume normalizado de biogás, GN e metano     | Nm³                                |
| `m_sub`                 | Massa úmida de substrato                      | t                                  |
| `V_D`, `V_G`            | Volume físico digestor e gasômetro            | m³; Nm³ quando estoque padronizado |
| `CF_y`                  | Fluxo líquido de custo do sistema energético  | BRL constantes de 2026             |
| `PKM_y`                 | Mobilidade atendida                           | passageiros·km                     |
| `GHG`                   | Emissões do sistema energético                | kgCO₂e                             |

**2 — Conjuntos e índices**

| Símbolo | Significado                        | Unidade |
|---------|------------------------------------|---------|
| S, s    | cenários de eletrificação          | —       |
| R, r    | arquiteturas tecnológicas          | —       |
| H_s, h  | intervalos cronológicos do cenário | —       |
| B_s, b  | ônibus sintéticos por cenário      | —       |
| G, g    | gabinetes de recarga               | —       |
| Y, y    | anos econômicos                    | ano     |
| M_y, m  | meses tarifários                   | mês     |
| D, d    | tipos de dia/índice de dia         | —       |
| x       | vetor de dimensionamento externo   | misto   |
| hdep    | intervalo de saída do ônibus       | —       |

**2 — Rede, solar e demanda**

| Símbolo                 | Significado                              | Unidade |
|-------------------------|------------------------------------------|---------|
| P_grid,h                | importação PCC                           | kW      |
| P_export,h              | exportação PCC                           | kW      |
| P_pv,h; P_curt,h        | PV utilizada; corte PV                   | kW      |
| φ_h                     | produção específica solar                | kW/kWp  |
| P_PV,ref,h; C_PV,ref    | referência solar; potência da referência | kW; kWp |
| C_PV,max; n_PV          | teto PV; índice inteiro da malha         | kWp; —  |
| L_base,h; L_charge,AC,h | carga base; recarga em AC                | kW      |
| L_aux,h; L_REV09,h      | auxiliares; demanda agregada REV09       | kW      |

**2 — BESS**

| Símbolo             | Significado                      | Unidade |
|---------------------|----------------------------------|---------|
| E_B,h; E_B,h+1      | energia armazenada no início/fim | kWh     |
| P_B,ch,h; P_B,dis,h | potência de carga/descarga       | kW      |
| u_B,h               | modo binário de carga            | 0/1     |
| η_ch; η_dis         | eficiências de carga e descarga  | —       |
| SOH_y               | estado de saúde da bateria       | —       |

**2 — CHP e biogás**

| Símbolo                            | Significado                             | Unidade            |
|------------------------------------|-----------------------------------------|--------------------|
| P_CHP,gross,h; P_CHP,net,h         | CHP bruto; CHP líquido                  | kWe                |
| u_CHP,h; a_h                       | estado de operação; disponibilidade     | 0/1                |
| P_aux,dig,h                        | auxiliares do digestor                  | kW                 |
| V_BG,prod,h; V_BG,cons,h           | biogás produzido; consumido             | Nm³/intervalo      |
| V_BG,stock,h; V_BG,loss,h          | estoque; perdas de biogás               | Nm³; Nm³/intervalo |
| V_GN,h; V_CH4,prod,h               | GN consumido; metano produzido          | Nm³/intervalo      |
| m_sub,h; m_sub,day                 | substrato por intervalo; por dia        | t; t/dia           |
| ρ; TRH                             | densidade; tempo de retenção            | t/m³; dia          |
| V_digestor,geom; V_gas_phys        | volumes físicos de digestor e gasômetro | m³                 |
| V_G,max                            | estoque máximo normalizado              | Nm³                |
| q_BG,ref; q_BG,max; q_prod,max     | vazões de referência e limites          | Nm³/h              |
| E_CH4,chemical,h; E_CHP,electric,h | energia química; elétrica CHP           | kWh                |

**2 — Ônibus e carregadores**

| Símbolo                          | Significado                               | Unidade    |
|----------------------------------|-------------------------------------------|------------|
| N_BEV,s; N_total                 | quantidades de ônibus elétricos; total    | ônibus     |
| E_route,b,d; E_drive,b,h         | energia de rota; consumo no intervalo     | kWh        |
| km_b,d; e_class(b)               | quilometragem; consumo específico         | km; kWh/km |
| C_b; E_bus,b,h                   | capacidade embarcada; energia embarcada   | kWh        |
| SOC_return,b,d; SOC_bus,b,h      | SOC retorno; SOC no intervalo             | fração     |
| P_charge,b,h^AC; P_charge,b,h^DC | potências de recarga AC e DC              | kW         |
| P_b,g,h^DC; a_b,g,h              | potência por gabinete; atribuição binária | kW; 0/1    |

**2 — Economia, ACV, exergia e objetivos**

| Símbolo                                   | Significado                                      | Unidade                  |
|-------------------------------------------|--------------------------------------------------|--------------------------|
| N_d; PKM_y; PKM_s,ano                     | peso de dias; serviço anual                      | dias/ano; passageiros·km |
| CAPEX_direct; CAPEX_total; CAPEX_y        | investimentos diretos, totais, anuais            | BRL2026                  |
| CF_0; CF_y; residual_y                    | fluxo inicial, anual e residual                  | BRL2026                  |
| OPEX_fixed,y; OPEX_variable,y             | operação fixa e variável                         | BRL2026                  |
| C_energy,y; C_demand,y; C_fuel,y          | energia, demanda, combustível                    | BRL2026                  |
| C_substrate,y; C_CGOB,y; C_replacement,y  | substrato, CGOB e reposições                     | BRL2026                  |
| τ_energy,h; τ_demand,m                    | tarifas de energia e demanda                     | BRL/kWh; BRL/(kW·mês)    |
| P_peak,m; z_s,r                           | pico mensal; epígrafe de pico                    | kW                       |
| F1; F2; F3                                | objetivos econômico, pico, ambiental             | BRL/PKM; kW; kgCO₂e/PKM  |
| GHG_assets; GHG_operation; GHG_EOL        | emissões incorporadas, operacionais, fim de vida | kgCO₂e                   |
| GHG_grid; GHG_upstream; GHG_fugitive      | emissões da rede, montante e fugitivas           | kgCO₂e                   |
| m_CH4,escaped                             | massa de metano emitida                          | kg                       |
| Ex_in; Ex_useful; Ex_destroyed; Ex_losses | parcelas do balanço exergético                   | kWh exergia              |

**Nota de consistência:** Esta seção complementa a tabela original; símbolos condicionais ou não parametrizados não constituem autorização de uso numérico. A unidade do índice h é adimensional; Δt é medido em horas.

**Convenção:** toda energia de fluxo é potência média × `Δt`. Não misturar Nm³/h com Nm³/intervalo; não misturar potência AC com DC sem a eficiência de conversão. Um parâmetro sem unidade definida não pode alimentar equação dimensional.

## A.3. Vetor de dimensionamento e condição de linearidade

**EQ-000 — Decisão externa.** `x=(C_PV,E_B,P_PCS,N_g,P_CHP,escolha_CHP,V_G,escala_digestor,r)` contém somente coordenadas cujo domínio e custo estejam documentados. Variáveis inteiras/categóricas devem usar operadores ou codificação mista explícitos. `x` é **fixado antes** de montar cada MILP. Para R0, `P_CHP=V_G=V_D=0`; R1/R3 não produzem biogás local; R2 incorpora digestão e estoque.

$$\mathbf{x} = \left( C_{PV},E_{B},P_{PCS},N_{g},P_{CHP},V_{G},V_{D},r \right)$$

**Propriedade matemática:** com `x` fixo, produtos `P_CHP·u_h`, `P_PCS·u_h`, `C_PV·φ_h` são coeficientes constantes multiplicados por variáveis binárias/contínuas, logo lineares. Não implementar simultaneamente `x` variável e `u_h` binária sem linearização exata e limites justificados. **Catálogo e domínio CHP ainda não demonstrados:** não inventar capacidades discretas.

**Onde:** x: vetor de dimensionamento externo; C_PV: capacidade fotovoltaica (kWp); E_B: capacidade BESS (kWh); P_PCS: potência do conversor (kW); N_g: número de gabinetes (inteiro); P_CHP: potência nominal CHP (kWe); V_G: armazenamento de gás (Nm³ de estoque, distinguindo volume físico); r: arquitetura. Escolha_CHP e escala_digestor são decisões de domínio ainda condicionado.

## A.4. Equações de despacho elétrico e PV

**EQ-001 — Balanço nodal AC sem déficit (kW).**

$$P_{h}^{grid} + P_{h}^{pv} + P_{h}^{chp,net} + P_{h}^{B,dis} = L_{h}^{base} + L_{h}^{charge,AC} + P_{h}^{B,ch} + L_{h}^{aux}$$

`P_grid,h + P_pv,h + P_chp,net,h + P_B,dis,h = L_base,h + L_charge,AC,h + P_B,ch,h + L_aux,h`

`L_base` e `L_charge` são mutuamente separados **somente se a origem dos dados comprovar essa decomposição**. No modo agregado, definir `L_REV09,h` conforme a semântica verificada das colunas e usar `L_REV09,h` no lugar de `L_base + L_charge`, **nunca somar a mesma recarga duas vezes**. Não introduzir slack de demanda como solução admissível. Teste: resíduo absoluto ≤ tolerância física documentada em todos os intervalos.

**Onde:** P_grid,h: importação no PCC (kW); P_pv,h: PV efetivamente utilizada (kW AC); P_chp,net,h: geração CHP líquida (kWe); P_B,dis,h e P_B,ch,h: descarga e carga BESS (kW AC); L_base,h: carga não veicular (kW); L_charge,AC,h: recarga veicular vista em AC (kW); L_aux,h: auxiliares não descontados da geração (kW); h: intervalo de 15 min. L_REV09,h substitui as cargas agregadas somente após verificação de sua semântica.

**EQ-002 — PCC e ausência de exportação (kW).**

$$0 \leq P_{h}^{grid} \leq 2500\ kW,\quad\quad P_{h}^{export} = 0$$

`0 ≤ P_grid,h ≤ 2500`, `P_export,h = 0`. Se houver carga do carregador em DC, converter para AC antes do balanço. A proibição de exportação implica que excedentes PV/CHP precisam ser cortados, armazenados ou ter despacho reduzido dentro dos limites físicos.

**Onde:** P_grid,h: potência importada (kW); P_export,h: potência exportada (kW); 2500: limite físico do PCC (kW); h: intervalo. A igualdade de exportação nula é uma restrição rígida.

**EQ-003 — Recurso solar normalizado.** `φ_h = P_PV,ref,h / C_PV,ref`, com unidade `kW/kWp` (numericamente adimensional), **somente após verificar qual potência nominal foi usada na série de referência**. Não reaplicar o fator de geração de aproximadamente 0,80 se já incorporado no CSV. A série horária de 8.760 pontos e a série de 15 min de 6.720 pontos não são intercambiáveis sem procedimento temporal documentado.

$$\phi_{h} = \frac{P_{h}^{PV,ref}}{C^{PV,ref}}$$

**Onde:** φ_h: produção PV específica no intervalo (kW/kWp); P_PV,ref,h: potência da série solar de referência (kW); C_PV,ref: capacidade nominal que originou a série (kWp); h: intervalo. A normalização requer comprovação da referência.

**EQ-004 — Potência PV e teto geométrico.**

$$0 \leq P_{h}^{pv} \leq C_{PV}\phi_{h},\quad\quad P_{h}^{curt} = C_{PV}\phi_{h} - P_{h}^{pv} \geq 0$$

`0 ≤ P_pv,h ≤ C_PV φ_h`; `P_curt,h = C_PV φ_h − P_pv,h ≥ 0`; `0 ≤ C_PV ≤ C_PV,max` e `C_PV = 25 n_PV` kWp para `n_PV` inteiro se o passo D06-005 for obrigatório no experimento. O teto base da Base Mestre é `1908,225 × 0,80 = 1526,58 kWp` (aproximadamente 1527); o fator de aproveitamento geométrico **não é o mesmo** que o fator de geração da série solar. Registrar arredondamento do teto para a malha de 25 kWp, sem exceder o limite físico.

**Onde:** P_pv,h: geração PV utilizada (kW); C_PV: potência nominal instalada (kWp); φ_h: fator de geração (kW/kWp); P_curt,h: corte fotovoltaico (kW); C_PV,max: teto geométrico (kWp); n_PV: número inteiro de módulos de capacidade de 25 kWp, se a discretização for mandatória.

**EQ-005 — Cortes e perdas.** `P_curt,h ≥ 0`; toda potência gerada e não usada precisa ter destino explícito. Perdas de conversão PV adicionais somente se a série aprovada não as incluir e houver parâmetro documentado.

$$P_{h}^{curt} \geq 0$$

**Onde:** P_curt,h: potência fotovoltaica disponível não aproveitada (kW); h: intervalo. O corte é distinto de perdas elétricas de conversão.

## A.5. BESS — estado, operação e envelhecimento

**EQ-006 — Balanço de energia BESS (kWh).**

$$E_{h + 1}^{B} = E_{h}^{B} + 0.922P_{h}^{B,ch}\Delta t - \frac{P_{h}^{B,dis}}{0.922}\Delta t$$

`E_B,h+1 = E_B,h + 0,922 P_B,ch,h Δt − (P_B,dis,h / 0,922) Δt`.

Os coeficientes são D07-008/009; o produto é `0,850084`, coerente com round-trip nominal 0,85 (D07-007, aproximação). Não ajustar unilateralmente as eficiências.

**Onde:** E_B,h e E_B,h+1: energia armazenada no início e fim do intervalo (kWh); P_B,ch,h e P_B,dis,h: potências AC de carga e descarga (kW); Δt: 0,25 h; η_ch=0,922 e η_dis=0,922: eficiências adimensionais (D07-008/009).

**EQ-007 — Faixa SOC.** `0,10 E_B SOH_y ≤ E_B,h ≤ 0,90 E_B SOH_y`, com `E_B` fixo no MILP. O limite deve valer também no estado terminal `h=H+1`.

$$0.10E_{B}SOH_{y} \leq E_{h}^{B} \leq 0.90E_{B}SOH_{y}$$

**Onde:** E_B: capacidade nominal do BESS (kWh); SOH_y: estado de saúde no ano y (fração); E_B,h: estoque de energia (kWh); 0,10 e 0,90: limites fracionários de SOC.

**EQ-008 — Potência PCS e exclusividade.**

$$0 \leq P_{h}^{B,ch} \leq P_{PCS}u_{h}^{B},\quad 0 \leq P_{h}^{B,dis} \leq P_{PCS}\left( 1 - u_{h}^{B} \right)$$

`0 ≤ P_B,ch,h ≤ P_PCS u_B,h`; `0 ≤ P_B,dis,h ≤ P_PCS(1−u_B,h)`; `u_B,h∈{0,1}`; `0 ≤ P_PCS ≤ 0,55 E_B` no caso-base. Não permitir carga e descarga simultâneas. Para `E_B=0`, exigir `P_PCS=0`.

**Onde:** P_B,ch,h e P_B,dis,h: potências de carga/descarga (kW); P_PCS: potência nominal do conversor (kW); u_B,h: variável binária de modo de carga; E_B: capacidade BESS (kWh); 0,55: limite C-rate em h⁻¹ (P_PCS/E_B).

**EQ-009 — Contornos cíclicos.** `E_B,1 = 0,50 E_B SOH_y`; `E_B,H+1 = E_B,1` **somente quando o horizonte modelado justificar fechamento cíclico**. Se dias representativos forem ligados cronologicamente, impor `E_B,final(d) = E_B,inicial(d+1)`; não reiniciar SOC em cada dia sintético.

$$E_{1}^{B} = 0.50E_{B}SOH_{y},\quad\quad E_{H + 1}^{B} = E_{1}^{B}\quad\text{(somente se fechamento ciclico autorizado)}$$

**Onde:** E_B,1: estoque inicial (kWh); E_B,H+1: estoque terminal (kWh); SOH_y: saúde da bateria (fração); d: dia ou bloco cronológico. A igualdade cíclica é condicional à representação temporal.

**EQ-010 — SOH e reposição.** `SOH_0=1`; `SOH` da primeira vida respeita o fim nominal 0,80 e degradação anual 0,0167, sem extrapolação silenciosa após o ano de reposição 12. O procedimento exato de atualização do SOH após reposição e a contabilização financeira/ambiental são **pendências de política temporal**. `SOH_y` é coeficiente exógeno do MILP, não variável livre.

$$SOH_{0} = 1,\quad\quad SOH_{y}\text{ e coeficiente exogeno do despacho}$$

**Onde:** SOH_y: estado de saúde da bateria no ano y (fração); SOH_0: valor inicial; 0,80: fim nominal de vida (fração); 0,0167: taxa anual nominal (ano⁻¹); y: ano econômico. Reposição requer política temporal documentada.

## A.6. CHP, gás natural, biogás e biodigestor

**EQ-011 — Despacho CHP ligado/desligado (kWe).**

$$0.50P_{CHP}u_{h}^{CHP} \leq P_{h}^{CHP,gross} \leq P_{CHP}u_{h}^{CHP}$$

`0,50 P_CHP u_CHP,h ≤ P_CHP,gross,h ≤ P_CHP u_CHP,h`; `u_CHP,h∈{0,1}`. Para `P_CHP=0`, despacho zero. Rampas, tempo mínimo ligado/desligado e catálogo de capacidades não devem ser assumidos sem especificação aprovada.

**Onde:** P_CHP: potência elétrica nominal bruta (kWe); P_CHP,gross,h: potência elétrica bruta despachada (kWe); u_CHP,h: decisão binária de operação; 0,50: fração mínima de carga ligada.

**EQ-012 — Indisponibilidade.** Para intervalo `a_h∈{0,1}` com disponibilidade operacional documentada: `u_CHP,h ≤ a_h`. D09-004=0,96 é parâmetro de disponibilidade de referência; **não** multiplicar potência ou produção de cada intervalo por 0,96. A construção da sequência `a_h` ainda requer regra validada.

$$u_{h}^{CHP} \leq a_{h}$$

**Onde:** u_CHP,h: estado ligado/desligado do CHP (binário); a_h: disponibilidade técnica no intervalo (binário); 0,96: disponibilidade agregada de referência, não fator de potência.

**EQ-013 — Energia do combustível.** Para GN: `P_CHP,gross,h Δt = 0,35 × 9,5 × V_GN,h`. Para biogás R2: `P_CHP,gross,h Δt = 0,35 × 6 × V_BG,cons,h`. Volumes em **Nm³ por intervalo**. Para R3, usar GN físico; o atributo CGOB é contábil, não altera PCI nem a natureza física do combustível.

$$P_{h}^{CHP,gross}\Delta t = \eta_{e}\, PCI_{f}\, V_{h}^{f}$$

**Onde:** P_CHP,gross,h: potência bruta CHP (kWe); Δt: duração (h); V_GN,h e V_BG,cons,h: volume consumido por intervalo (Nm³); 0,35: eficiência elétrica; 9,5 e 6: PCI do GN e do biogás (kWh/Nm³).

**EQ-014 — Auxiliares e fronteira bruto/líquido.** Em R2: `P_aux,dig,h = 0,05 P_CHP,gross,h` conforme D08-013. Usar **uma** convenção: ou `P_CHP,net = P_CHP,gross − P_aux,dig` e excluir essa parcela de `L_aux`, ou usar CHP bruto e incluir auxiliares no lado de consumo. Não fazer ambas.

$$P_{h}^{aux,dig} = 0.05P_{h}^{CHP,gross}$$

**Onde:** P_aux,dig,h: potência elétrica auxiliar da biodigestão (kW); P_CHP,gross,h e P_CHP,net,h: potências bruta e líquida CHP (kWe); 0,05: consumo auxiliar proporcional. A parcela auxiliar só pode aparecer uma vez no balanço.

**EQ-015 — Separação de combustíveis.** `V_BG,cons,h ≥ 0`, `V_GN,h ≥ 0`; arquitetura R1/R3 impõe `V_BG,cons,h=0`; R2 impõe `V_GN,h=0` na fronteira de CHP a biogás. Mistura não é permitida sem decisão documentada.

$$V_{h}^{BG,cons} \geq 0,\quad V_{h}^{GN} \geq 0$$

**Onde:** V_BG,cons,h: volume de biogás consumido (Nm³/intervalo); V_GN,h: volume de gás natural consumido (Nm³/intervalo); R1/R2/R3: arquiteturas de combustível; h: intervalo.

**EQ-016 — Produção de biogás (Nm³).**

$$V_{h}^{CH4,prod} = 60m_{h}^{sub},\quad\quad V_{h}^{BG,prod} = \frac{V_{h}^{CH4,prod}}{0.60}$$

`V_CH4,prod,h = 60 m_sub,h`; `V_BG,prod,h = V_CH4,prod,h / 0,60 = 100 m_sub,h`.

`m_sub,h` é tonelada úmida de substrato processado no intervalo, não tonelada por dia. A alimentação garantida tem quantidade endógena (D08-004); não significa substrato ilimitado sem dimensionamento/custo. O modelo simplificado de conversão imediata não substitui a dinâmica de TRH; se adotado, requer decisão explícita.

**Onde:** V_CH4,prod,h: volume normalizado de metano produzido (Nm³/intervalo); V_BG,prod,h: biogás produzido (Nm³/intervalo); m_sub,h: massa úmida processada (t/intervalo); 60: rendimento (Nm³ CH4/t); 0,60: fração volumétrica de metano.

**EQ-017 — Estoque de biogás.** `V_BG,stock,h+1 = V_BG,stock,h + V_BG,prod,h − V_BG,cons,h − V_BG,loss,h`, tudo em Nm³/intervalo. `V_BG,loss,h ≥ 0` é fluxo físico a fundamentar; **não escolher zero apenas para viabilizar o modelo**. Especificar estoque inicial, final e limite de armazenamento antes de R2 completo.

$$V_{h + 1}^{BG,stock} = V_{h}^{BG,stock} + V_{h}^{BG,prod} - V_{h}^{BG,cons} - V_{h}^{BG,loss}$$

**Onde:** V_BG,stock,h: estoque de biogás no início do intervalo (Nm³); V_BG,prod,h: produção (Nm³/intervalo); V_BG,cons,h: consumo (Nm³/intervalo); V_BG,loss,h: perdas (Nm³/intervalo); h+1: estado final.

**EQ-018 — Volume do biodigestor.** Para alimentação média `m_sub,day` em t/dia, densidade `ρ=1 t/m³`, TRH 30 dias e fração útil 0,80: `V_digestor,geom ≥ (m_sub,day/ρ) × 30 / 0,80` m³. Diferenciar volume geométrico de capacidade de processamento em t/ano usada no CAPEX D08-008.

$$V^{dig,geom} \geq \frac{m^{sub,day}}{\rho}\frac{30}{0.80}$$

**Onde:** V_digestor,geom: volume geométrico do biodigestor (m³); m_sub,day: massa processada por dia (t/dia); ρ: densidade da mistura (t/m³); 30: TRH (dias); 0,80: fração útil do volume.

**EQ-019 — Capacidade do gasômetro.** `0 ≤ V_BG,stock,h ≤ V_G,max` em Nm³ de gás nas condições normalizadas. A referência de autonomia de 8 h deve relacionar `V_G,max` à vazão de consumo CHP na condição definida: `V_G,max ≥ 8 × q_BG,ref` (Nm³/h). `q_BG,ref` e a conversão de volume normalizado para m³ de equipamento precisam de definição documental; não igualar automaticamente Nm³ a m³ físicos.

$$0 \leq V_{h}^{BG,stock} \leq V^{G,max},\quad\quad V^{G,max} \geq 8q^{BG,ref}$$

**Onde:** V_BG,stock,h: estoque de gás (Nm³); V_G,max: capacidade máxima normalizada do gasômetro (Nm³); q_BG,ref: vazão de referência (Nm³/h); 8: autonomia (h). Volume geométrico físico exige conversão documentada.

**EQ-020 — Compatibilidade de fluxo/armazenamento.** `V_BG,cons,h / Δt ≤ q_BG,max` e `V_BG,prod,h / Δt ≤ q_prod,max` **somente quando limites de vazão fundamentados estiverem disponíveis**. Para tratamento, CAPEX em R\$/(Nm³/h) usa vazão nominal, não volume total produzido. A continuidade de estoques entre dias aplica-se também ao gasômetro.

$$\frac{V_{h}^{BG,cons}}{\Delta t} \leq q^{BG,max},\quad\frac{V_{h}^{BG,prod}}{\Delta t} \leq q^{prod,max}$$

**Onde:** V_BG,cons,h e V_BG,prod,h: volumes consumido e produzido por intervalo (Nm³); Δt: duração (h); q_BG,max e q_prod,max: limites de vazão (Nm³/h), somente se documentados.

**EQ-021 — Consistência energética de R2.** `E_CH4,chemical,h = V_BG,cons,h × 6 kWh/Nm³`; `E_CHP,electric,h = 0,35 E_CH4,chemical,h`; a fração de metano 0,60 já está embutida no PCI do biogás, não deve ser aplicada uma segunda vez.

$$E_{h}^{CHP,electric} = 0.35\, V_{h}^{BG,cons}\,\left( 6\ kWh/Nm^{3} \right)$$

**Onde:** E_CH4,chemical,h: energia química do biogás (kWh); E_CHP,electric,h: energia elétrica bruta CHP (kWh); V_BG,cons,h: consumo de biogás (Nm³); 6: PCI do biogás (kWh/Nm³); 0,35: rendimento elétrico.

## A.7. Recarga individual e gabinetes duplos — especificação fechada, dados ainda ausentes

**EQ-029 — Cenários e frota.** `N_BEV,s ∈ {100,200,300,375,450}`, `N_total=450` sintéticos. Participações de classes são 30%/30%/25%/15%. Quando a multiplicação não produzir inteiros, exigir regra determinística documentada de distribuição, preservando soma exata, sem inventar a alocação atual.

$$N_{s}^{BEV} \in \{ 100,200,300,375,450\},\quad\quad N^{total} = 450$$

**Onde:** N_BEV,s: ônibus elétricos do cenário s (unidades); N_total: frota sintética total (unidades); percentuais 30/30/25/15: participações das quatro classes veiculares.

**EQ-030 — Consumo de rota e SOC (kWh e fração).** `E_route,b,d = km_b,d e_class(b)`; `SOC_return,b,d = 0,95 − E_route,b,d/C_b`; `SOC_return,b,d ≥ 0,10`. A expressão é uma verificação de factibilidade da rota sintética, não evidência de viagem/veículo físico.

$$E_{b,d}^{route} = km_{b,d}e_{class(b)},\quad\quad SOC_{b,d}^{return} = 0.95 - \frac{E_{b,d}^{route}}{C_{b}}$$

**Onde:** E_route,b,d: energia consumida na rota (kWh); km_b,d: distância do ônibus b no dia d (km); e_class(b): consumo específico da classe (kWh/km); C_b: capacidade da bateria embarcada (kWh); SOC_return,b,d: fração de carga ao retornar.

**EQ-031 — Dinâmica da energia no ônibus.** `E_bus,b,h+1 = E_bus,b,h + 0,95 P_charge,b,h^AC Δt − E_drive,b,h`, com `E_drive,b,h` em kWh no intervalo da viagem. `SOC_bus,b,h=E_bus,b,h/C_b`; `0,10 C_b ≤ E_bus,b,h ≤ C_b`. Nas saídas obrigatórias `E_bus,b,hdep ≥ 0,95 C_b`. Não impor recarga fora da janela de conexão.

$$E_{b,h + 1}^{bus} = E_{b,h}^{bus} + 0.95P_{b,h}^{charge,AC}\Delta t - E_{b,h}^{drive}$$

**Onde:** E_bus,b,h: energia da bateria do ônibus b no intervalo h (kWh); P_charge,b,h^AC: potência de recarga no lado AC (kW); E_drive,b,h: energia de tração debitada no intervalo (kWh); C_b: capacidade embarcada (kWh); 0,95: eficiência AC/DC e SOC de saída conforme a posição na expressão.

**EQ-032 — Conversão AC/DC.** `P_charge,b,h^DC = 0,95 P_charge,b,h^AC`; `0 ≤ P_charge,b,h^DC ≤ 150 kW` para cada ônibus. No balanço AC, usar `P_charge^AC` uma única vez.

$$P_{b,h}^{charge,DC} = 0.95P_{b,h}^{charge,AC}$$

**Onde:** P_charge,b,h^DC: potência entregue em DC (kW); P_charge,b,h^AC: potência absorvida da rede AC (kW); 0,95: eficiência de conversão; 150: potência máxima por ônibus (kW DC).

**EQ-033 — Gabinete dual e atribuição.** Para `a_b,g,h∈{0,1}`: `Σ_g a_b,g,h ≤ 1`; `Σ_b a_b,g,h ≤ 2`; `0 ≤ P_b,g,h^DC ≤ 150 a_b,g,h`; `Σ_b P_b,g,h^DC ≤ 150 kW`; `P_charge,b,h^DC = Σ_g P_b,g,h^DC`. Exigir `a_b,g,h=0` fora da disponibilidade. A capacidade total do gabinete é 150 kW, **não 300 kW**.

$$\sum_{b}^{}P_{b,g,h}^{DC} \leq 150\ kW,\quad\quad\sum_{b}^{}a_{b,g,h} \leq 2$$

**Onde:** a_b,g,h: binária de atribuição do ônibus b ao gabinete g no intervalo h; P_b,g,h^DC: potência DC alocada (kW); P_charge,b,h^DC: soma das alocações ao ônibus (kW); Σ_g e Σ_b: somas sobre gabinetes e ônibus; 2: número de saídas por gabinete; 150: limite compartilhado (kW DC).

**EQ-034 — Atendimento obrigatório.** Para cada ônibus e saída obrigatória, `E_bus,b,hdep ≥ 0,95 C_b`; nenhum déficit de recarga pode ser convertido em penalidade que faça solução inviável parecer factível. **B02 permanece aberto:** falta matriz de identidade, viagens, SOC, conexão e horários por veículo. Logo EQ-031–034 não podem ser executadas fielmente com o CSV agregado REV09.

$$E_{b,h^{dep}}^{bus} \geq 0.95C_{b}$$

**Onde:** E_bus,b,hdep: energia embarcada na saída obrigatória (kWh); C_b: capacidade nominal embarcada (kWh); 0,95: SOC mínimo de saída; hdep: instante de partida do ônibus b.

## A.8. Horizonte temporal, anualização e cenários

**EQ-035 — Dias-tipo e PKM.** `N_úteis=250`, `N_sáb=52`, `N_dom=63`, soma 365. Para um cenário com distribuição documentada: `PKM_s,ano = 23 Σ_d N_d Σ_b km_b,d` passageiros·km/ano. Essa fórmula exige a definição do conjunto de ônibus efetivamente atendidos e da correspondência de dias-tipo. O valor histórico de PKM é **exploratório**, não substitui a construção documentada.

$$PKM_{s,ano} = 23\sum_{d}^{}N_{d}\sum_{b}^{}km_{b,d}$$

**Regra temporal mandatória:** a série de demanda possui 70 dias sintéticos, enquanto a solar 15 min possui 70 dias datados em 2025; igualdade de índices não comprova igualdade de datas. **B01 permanece aberto**. Os cenários 2038 e 2050 não são automaticamente anos consecutivos de um VPL iniciado em 2026; definir experimento por ano de referência ou cronograma de transição explícito antes de F1/F3 definitivos.

**Onde:** PKM_s,ano: serviço anual (passageiros·km); N_d: dias anuais do tipo d (dias/ano); km_b,d: distância percorrida (km/dia); b: ônibus efetivamente atendido; 23: ocupação média (passageiros/ônibus).

## A.9. Custos, tarifação e F1

**EQ-036 — CAPEX (BRL2026).** `CAPEX_direct = 4000 C_PV + 1500 E_B + 900 P_PCS + 250000 N_g + c_CHP,r P_CHP + 500 Cap_dig[t/ano] + 1000 q_treat[Nm³/h] + 1500 V_gas_phys[m³]`, **somando apenas termos aplicáveis à arquitetura**. `c_CHP,R2=8000 R$/kWe`; `c_CHP,R1/R3=6000 R$/kWe`. `CAPEX_total = CAPEX_direct(1+0,10)` para engenharia/contingência, observada a fronteira de itens elegíveis. Não aplicar custo de gasômetro em Nm³ sem converter para m³ físico de projeto.

$$CAPEX_{total} = 1.10\, CAPEX_{direct}$$

**Onde:** CAPEX_direct e CAPEX_total: investimentos em BRL2026; C_PV (kWp), E_B (kWh), P_PCS (kW), N_g (gabinetes), P_CHP (kWe), Cap_dig (t/ano), q_treat (Nm³/h), V_gas_phys (m³): bases dimensionais dos custos unitários; c_CHP,r: custo CHP da arquitetura r (BRL/kWe); 0,10: engenharia/contingência.

**EQ-037 — Fluxo de caixa anual (BRL2026/ano).** `CF_y = CAPEX_y + OPEX_fixed,y + OPEX_variable,y + C_energy,y + C_demand,y + C_fuel,y + C_substrate,y + C_CGOB,y + C_replacement,y − residual_y`. Custos específicos: OPEX PV 1,5% CAPEX/ano; BESS 2,5%; CHP 4%; digestão/tratamento 5%; gasômetro 2%; carregadores 2%. GN entregue R\$3/Nm³; substrato R\$50/t e transporte/preparo R\$40/t; prêmio CGOB R\$0,10/Nm³ equivalente. Reposição inversor PV ano 12 a 15% CAPEX PV; bateria ano 12 a 60% CAPEX inicial bateria; reforma CHP ano 10 a 25% CAPEX inicial CHP. Respeitar arquitetura, contagem de reposições e convenção temporal.

$$CF_{y} = CAPEX_{y} + OPEX_{y} + C_{y}^{energy} + C_{y}^{demand} + C_{y}^{fuel} + C_{y}^{substrate} + C_{y}^{CGOB} + C_{y}^{replacement} - residual_{y}$$

**Onde:** CF_y: custo líquido no ano y (BRL2026); CAPEX_y: investimentos; OPEX_fixed,y e OPEX_variable,y: operação/manutenção; C_energy,y: energia; C_demand,y: demanda; C_fuel,y: combustível; C_substrate,y: substrato/logística; C_CGOB,y: atributo; C_replacement,y: reposições; residual_y: recuperação de valor. Todas as parcelas em BRL2026.

**EQ-038 — Energia comprada.** `C_energy,y = Σ_{h∈y} P_grid,h Δt × τ_energy,h`, com `τ_energy=0,75 BRL/kWh` como **hipótese-base D05-003**, se o experimento assumir tarifa uniforme. A4 Verde ponta/fora ponta é referência alternativa, **não substituição automática**. Se a série de 70 dias não tiver anualização homologada, `C_energy,y` definitivo não é calculável.

$$C_{y}^{energy} = \sum_{h \in y}^{}P_{h}^{grid}\Delta t\,\tau_{h}^{energy}$$

**Onde:** C_energy,y: despesa anual de energia (BRL2026); P_grid,h: potência comprada (kW); Δt: 0,25 h; τ_energy,h: tarifa de energia (BRL/kWh); h∈y: intervalos representativos anualizados mediante regra validada.

**EQ-039 — Demanda tarifária.** `C_demand,y = Σ_{m∈y} τ_demand,m × P_peak,m`, com `P_peak,m ≥ P_grid,h` para `h∈m`; `τ_demand=30 BRL/(kW·mês)` como hipótese-base D05-004. Não multiplicar pico único de 70 dias por 12 sem regra temporal/contratual documentada. Tarifa e pico de demanda são distintos do objetivo F2.

$$C_{y}^{demand} = \sum_{m \in y}^{}\tau_{m}^{demand}P_{m}^{peak},\quad P_{m}^{peak} \geq P_{h}^{grid}\ \forall h \in m$$

**Onde:** C_demand,y: despesa anual de demanda (BRL2026); m: mês tarifário; τ_demand,m: tarifa (BRL/kW/mês); P_peak,m: maior potência importada no mês (kW); P_grid,h: importação no intervalo (kW).

**EQ-040 — F1 (BRL/PKM).**

$$F_{1} = \frac{CF_{0} + \sum_{y = 1}^{20}\frac{CF_{y}}{(1 + 0.12)^{y}}}{\sum_{y = 1}^{20}\frac{PKM_{y}}{(1 + 0.12)^{y}}}$$

`F1 = [CF_0 + Σ_{y=1}^{20} CF_y/(1+0,12)^y] / [Σ_{y=1}^{20} PKM_y/(1+0,12)^y]`.

`CF_0` contém investimento inicial quando desembolsado em `t=0`. O numerador é VPL dos custos do sistema energético; o denominador é VPL dos PKM, sem fabricação/operação do ônibus fora da fronteira definida. O denominador deve ser estritamente positivo. Sensibilidades da taxa real: 6% e 18%. `F1` permanece bloqueada para avaliação definitiva enquanto calendário, fluxos e PKM não forem reconciliados.

**Onde:** F1: custo presente por serviço presente (BRL2026/PKM); CF_0: desembolso inicial (BRL2026); CF_y: custo líquido anual (BRL2026); PKM_y: passageiros·km anuais; y: ano 1 a 20; 0,12: taxa real anual de desconto.

## A.10. Pico de importação F2

**EQ-041 — F2 (kW).** `F2_s,r(x) = min_{despacho factível} z_s,r` quando o MILP for formulado para minimizar pico, sujeito a `z_s,r ≥ P_grid,h` para todo `h∈H_s`. Se o despacho interno otimizar outra função, o valor relatado é `max_h P_grid,h` da solução escolhida, não o mínimo possível de pico. **O critério de desempate/despacho interno precisa ser explicitamente fixado antes do NSGA-II**; não presumir que a mesma solução minimiza custo e pico. Comparar F2 apenas no mesmo cenário e domínio temporal.

$$F_{2} = \max_{h \in H_{s}}P_{h}^{grid}$$

**Onde:** F2_s,r(x): objetivo de pico da arquitetura r no cenário s para dimensionamento x (kW); z_s,r: variável epigráfica de pico (kW); P_grid,h: importação no PCC (kW); H_s: conjunto de intervalos avaliados. O mínimo depende da função efetivamente otimizada pelo MILP.

## A.11. ACV, fronteiras e F3

**EQ-042 — Emissões incorporadas (kgCO₂e).** `GHG_assets = 900 C_PV + 135 E_B + 32,47 Cap_dig[t/ano] + 11,6280409 V_gas_phys[m³] + 105 P_CHP + GHG_PCS + GHG_chargers + GHG_PV_inverter + GHG_EOL + GHG_replacements`, com parcelas apenas aplicáveis e unidades funcionais compatíveis. **D11-013=135** é fator condicional; D11-014/018/019 permanecem sem fator; D11-004 legado de reposição BESS não deve substituir automaticamente a emissão real de fabricação do equipamento de reposição.

$$GHG_{assets} = GHG_{PV} + GHG_{BESS} + GHG_{CHP} + GHG_{dig} + GHG_{gas} + GHG_{PCS} + GHG_{chargers} + GHG_{other}$$

**Onde:** GHG_assets: emissões incorporadas (kgCO₂e); C_PV (kWp), E_B (kWh), Cap_dig (t/ano), V_gas_phys (m³), P_CHP (kWe): bases dos fatores; GHG_PCS, GHG_chargers, GHG_PV_inverter, GHG_EOL, GHG_replacements: parcelas adicionais em kgCO₂e, sujeitas a fatores válidos.

**EQ-043 — Emissões operacionais (kgCO₂e).** `GHG_operation = GHG_grid + GHG_GN_upstream+combustion + GHG_substrate_logistics + GHG_other`; para SIN, selecionar **uma** fronteira consistente: D11-002=0,0461 kgCO₂/kWh (operacional legado) **ou** D11-017=0,0996 kgCO₂e/kWh gerado (ACV histórica condicionada), sem soma direta e sem tratar energia gerada no SIN como energia entregue na garagem sem ajuste documentado. D11-015/016 ausentes.

$$GHG_{grid} = \sum_{h}^{}E_{h}^{grid}EF_{h}^{grid}$$

**Onde:** GHG_operation: emissões operacionais totais (kgCO₂e); GHG_grid: emissões da eletricidade comprada; GHG_GN_upstream+combustion: cadeia e combustão GN; GHG_substrate_logistics: transporte/preparo do substrato; GHG_other: outras parcelas documentadas. Fatores SIN alternativos não são aditivos.

**EQ-044 — Metano fugitivo e slip (kgCO₂e).** `GHG_CH4 = m_CH4,escaped[kg] × 27 kgCO₂e/kgCH4` para metano biogênico sob a fronteira aplicável. Frações D11-008=0,006 e D11-009=0,017 devem ser aplicadas à **base física correta e não sobreposta** (volume ou massa de metano em estágio identificado); converter Nm³ CH4 para kg com densidade normalizada documentada. Não inventar densidade nem confundir biogás total com CH4 puro.

$$GHG_{CH4} = m_{CH4}^{escaped}\,\left( 27\ kgCO_{2}e/kgCH_{4} \right)$$

**Onde:** GHG_CH4: impacto do metano emitido (kgCO₂e); m_CH4,escaped: massa fugitiva de CH4 (kg); 27: potencial de aquecimento global do metano biogênico (kgCO₂e/kgCH4); D11-008/009: frações de perda cuja base física deve ser identificada.

**EQ-045 — F3 (kgCO₂e/PKM).** `F3 = (GHG_assets + GHG_replacements + GHG_operation + GHG_upstream + GHG_fugitive + GHG_EOL − credits_approved) / Σ_y PKM_y`, com mesma fronteira de horizonte e serviço do experimento. Créditos de digestato e tratamento evitado são zero conforme D11-011/012, não licença para ignorar emissões ausentes. **F3 completa não é computável com fatores D11-014/015/016/018/019 ausentes.** Resultados parciais devem ser rotulados e nunca utilizados como F3 definitiva do NSGA-II triobjetivo.

$$F_{3} = \frac{GHG_{assets} + GHG_{replacements} + GHG_{operation} + GHG_{upstream} + GHG_{fugitive} + GHG_{EOL} - credits_{approved}}{\sum_{y}^{}PKM_{y}}$$

**Onde:** F3: emissões por serviço (kgCO₂e/PKM); GHG_assets: fabricação/implantação; GHG_replacements: substituições; GHG_operation: operação; GHG_upstream: cadeias a montante; GHG_fugitive: fugitivas; GHG_EOL: fim de vida; credits_approved: créditos aprovados; PKM_y: serviço anual. Exigir fronteiras não sobrepostas entre parcelas.

## A.12. Exergia complementar

**EQ-046 — Balanço exergético, apenas pós-processamento.** `Ex_in = Ex_useful + Ex_destroyed + Ex_losses` \[kWh de exergia\], sob fronteira e ambiente de referência definidos. Não calcular eficiência exergética ou destruição com `PCI` como se fosse exergia química sem convenção/fator documentado. Exergia não é F4.

$$Ex_{in} = Ex_{useful} + Ex_{destroyed} + Ex_{losses}$$

**Onde:** Ex_in: exergia de entrada; Ex_useful: exergia útil; Ex_destroyed: destruição por irreversibilidades; Ex_losses: perdas para o exterior. Todas as parcelas em kWh de exergia; temperatura/estado de referência ainda requerem especificação.

## A.13. Função de avaliação do NSGA-II e contrato do MILP

**ALG-001.** Para cada `(s,r,x)` validado: (i) checar domínios e arquitetura; (ii) fixar `x`; (iii) construir MILP com dados de cenário imutáveis; (iv) resolver com HiGHS; (v) registrar status, gap e tolerâncias; (vi) testar balanços e fronteiras; (vii) rejeitar solução com déficit, violações ou status não aceito; (viii) calcular indicadores disponíveis em módulo independente; (ix) armazenar rastreabilidade de parâmetros, hash, solver e seed. **Não devolver objetivos numéricos falsos para configurações inviáveis.** Para avaliação triobjetiva, exigir F1/F2/F3 completos e comparáveis; até lá, o protótipo pode operar como teste de despacho e, quando justificado, com objetivos parciais claramente separados.

A escolha da função escalar do MILP interno (custo operacional, pico ou combinação lexicográfica) **não está fechada por estas fontes**. Esta é uma decisão matemática material: não impor uma preferência sem registro. Os hiperparâmetros do NSGA-II (população, gerações e seeds) são parâmetros experimentais ainda a definir, não valores físicos a inventar.

## A.14. Condições de contorno, teste de conservação e aceite

| Teste | Aceite exigido                                                            |
|-------|---------------------------------------------------------------------------|
| T-001 | Todas as 137 IDs presentes e únicas; valores idênticos à Base Mestre      |
| T-002 | `Δt=0,25 h`; unidade consistente em cada equação                          |
| T-003 | Demanda agregada e individual mutuamente exclusivas                       |
| T-004 | Resíduo EQ-001 em todos os intervalos dentro da tolerância declarada      |
| T-005 | PCC ≤ 2500 kW; exportação = 0; déficit = 0                                |
| T-006 | PV usado + cortado = PV disponível, sem duplicação de fator               |
| T-007 | BESS conserva energia com 0,922/0,922; limites SOC e exclusividade        |
| T-008 | CHP desligado = 0; ligado 50–100%; sem 0,96 multiplicativo                |
| T-009 | R2 conserva Nm³ biogás; metano e combustível não confundidos              |
| T-010 | Recarga dual soma ≤ 150 kW DC/gabinete, ≤ 2 conectores                    |
| T-011 | SOC ônibus em saída ≥ 95% e disponibilidade por ônibus, somente após B02  |
| T-012 | 70 dias não anualizados sem correspondência aprovada                      |
| T-013 | F1 com VPL BRL/PKM em horizonte e convenção compatíveis                   |
| T-014 | F2 como máximo do mesmo domínio do experimento                            |
| T-015 | F3 bloqueada se fator ACV obrigatório estiver ausente                     |
| T-016 | Cada equação → parâmetro(s) → constraint Pyomo → teste unitário/regressão |

**Estado de congelamento:** equações EQ-001–010 e EQ-041 são especificações operacionais prontas para codificação do protótipo agregado, condicionadas à interpretação dos CSV e ao fechamento temporal. EQ-011–021, EQ-029–040 e EQ-042–046 definem a matemática e seus limites, **mas não autorizam execução científica completa** enquanto houver entradas e decisões não resolvidas. A lacuna não pode ser ocultada por zero, interpolação arbitrária ou solução inviável penalizada.

## A.15. Rastreabilidade dos 137 parâmetros e controle de versão

O anexo `D28_Especificacao_Rastreabilidade_137_IDs.csv` enumera **todos os 137 IDs** com valor e unidade original, destino matemático principal, estado de uso e colunas reservadas para o nome exato da constraint Pyomo e teste. `META`/`GOV`/`HIST` indicam metadados, governança e registros históricos; não se força sua transformação em coeficiente. O mapeamento é **de especificação**, não uma alegação de que o código existe ou foi validado.

Qualquer mudança futura exige registro de: ID da decisão, motivação, equações afetadas, IDs de parâmetros, testes alterados, impacto na comparabilidade e aprovação. Alterações não aprovadas não entram na branch principal. O PC-REV07 e a Base Mestre permanecem imutáveis.



## Anexo B — Matriz de entregáveis, tabelas e aceitação

| Código | Entregável | Origem verificável | Condição de publicação |
|---|---|---|---|
| TAB-01 | Matriz de cenários, arquiteturas e horizontes | `config/experiments` e manifestos | Sempre, com status |
| TAB-02 | Entradas, capacidades e unidades | Base Mestre + `design_variables.csv` | IDs e fontes presentes |
| TAB-03 | Factibilidade e status do solver | `candidates_all.csv` | Todos os candidatos contabilizados |
| TAB-04 | Objetivos por solução elegível | `candidates_feasible.csv` | Estados F1/F2/F3 explícitos |
| TAB-05 | Indicadores de frentes e comparação | `pareto_3d.csv`, `convergence.csv` | Apenas objetivos completos e comparáveis |
| FIG-P01 | Pareto tridimensional F1/F2/F3 | `pareto_3d.csv` | Três objetivos homologados |
| FIG-P02–04 | Projeções da frente 3D | `pareto_3d.csv` | Rotular como projeções |
| FIG-P05 | Evolução por geração | `convergence.csv` | Indicador e referência documentados |
| FIG-P06 | Dimensionamentos não dominados | `design_variables.csv` | Mesmo conjunto auditado |
| FIG-P07 | Perfis cronológicos de despacho | `dispatch_timeseries` | Balanços e domínio válidos |
| FIG-C01 | Sobreposição de R0–R3 por cenário | frentes comparáveis | Fronteiras uniformes |
| FIG-C02 | Comparação entre cenários | frentes comparáveis | Não atribuir variação só ao ano |
| MAN-01 | Manifesto de execução e figuras | JSON/CSV + SHA-256 | Reprodutível |

**Regra final:** a aprovação documental do PC-REV08 não constitui homologação dos parâmetros pendentes nem dos resultados. Toda figura e tabela deve apontar a execução, fonte de dados, filtro e hash que permitam sua regeneração.
