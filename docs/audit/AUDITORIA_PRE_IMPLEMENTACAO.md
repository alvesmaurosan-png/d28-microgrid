# Auditoria de consistência documental pré-implementação — D28 / PC-REV08

**Data:** 18/10/2026. **Estado:** auditoria documental e estrutural; NÃO equivale à homologação científica.

## 1. Corpus examinado

- `PC_REV08_Protocolo_Cientifico_Tecnico_Consolidado.md`; `D28_Documento_Final_Consolidado_REV03_PC_REV08.md`; `Tutorial_D28_PyCharm_GitHub_PC_REV08_REV01.md`.
- `D28_Especificacao_Rastreabilidade_137_IDs.csv`; ZIP definitivo PC-REV07; CSV de bloqueios, solar e demanda do ZIP.
- A Base Mestre do ZIP foi copiada sem alteração.

## 2. Achados e decisões

| ID | Gravidade | Constatação | Encaminhamento |
|---|---|---|---|
| AC-01 | ALTA | Tutorial introdução ainda declara PC-REV07 como referência normativa apesar da seção 26 apontar PC-REV08 | Atualizar introdução e árvore documental na próxima revisão controlada. |
| AC-02 | MÉDIA | PC-REV08 prevê reporting/plots.py; tutorial seção 27 menciona reporting/figures.py | Unificar API em plots.py ou alterar ambos formalmente. |
| AC-03 | ALTA | ZIP de entradas preserva PC-REV07 e não inclui PC-REV08; rastreabilidade da baseline depende de documentação externa | Conservar ZIP imutável e referenciar PC-REV08 em docs/protocolo, com hashes. |
| AC-04 | CRÍTICA | B01 aberto: solar_local_hour repetido por intervalos de 15 min; não comprova pareamento civil | Não efetuar casamento por índice como cronologia validada. |
| AC-05 | CRÍTICA | B02 aberto: não há matriz individual de viagens/SOC/janelas | Somente R0 agregado sintético para smoke; nenhuma factibilidade individual. |
| AC-06 | CRÍTICA | B04 aberto: F3 ACV incompleta (D11-014/015/016/018/019) | Não exportar Pareto triobjetiva. |
| AC-07 | ALTA | B03 e B06 não fechados; tarifa, anualização e PKM ainda condicionais | Não calcular F1 definitivo. |
| AC-08 | ALTA | Critério escalar/lexicográfico do MILP interno não decidido | Não integrar NSGA-II como resultado científico. |
| AC-09 | MÉDIA | Matriz 137 IDs mantém Código_Pyomo e Teste como A IMPLEMENTAR em muitos registros | Fechar rastreabilidade ID→equação→código→teste progressivamente. |
| AC-10 | MÉDIA | Protocolo proposto PC-REV08 ainda não aprovado formalmente | Registrar aprovação M0 antes de congelamento normativo. |
| AC-11 | MÉDIA | Tutorial possui árvore histórica src/d28/reporting.py e scripts antigos, além do novo layout de reporting | Declarar nova árvore única de referência e deprecar exemplo anterior. |
| AC-12 | MÉDIA | Critérios de tolerância de dominância e repetibilidade precisam de decisão formal | Código usa dominância exata para testes unitários, sem assumir tolerância científica. |

## 3. Auditoria de parâmetros

- Linhas na matriz: **137**; IDs únicos: **137**.
- Valores não foram alterados nem lacunas preenchidas.
- Fatores ambientais ausentes continuam pendentes.

## 4. Gates e liberação

| Gate | Estado de execução neste pacote | Evidência / restrição |
|---|---|---|
| M0 | CONDICIONADO | Divergências documentais AC-01/02/11 e aprovação formal pendentes |
| M1 | EXECUTADO estruturalmente | Ingestão, contagens, intervalos e SHA-256 local; sem reconciliação civil |
| M2 | PARCIAL (smoke) | Modelo Pyomo R0 mínimo de 2–4 intervalos; não representa formulação física completa |
| M3 | NÃO INICIADO | CHP, biogás, catálogo e B05 |
| M4 | BLOQUEADO | Matriz por ônibus ausente (B02) |
| M5 | BLOQUEADO para F1/F3 | B03, B04, B06; F2 apenas função utilitária |
| M6 | BLOQUEADO | MILP interno e indicadores não homologados |
| M7 | BLOQUEADO | Sem resultados científicos para figuras Pareto |

## 5. Critérios de saída para continuidade

1. Aprovar formalmente PC-REV08 e resolver referências conflitantes em tutorial/documento.
2. Reconciliar série solar × demanda por calendário (B01) e fornecer matriz individual de recarga (B02).
3. Definir critério interno de despacho MILP e tolerâncias numéricas.
4. Homologar tarifas, anualização/PKM, inventário ACV e tecnologias condicionais.
5. Implementar e testar o despacho completo antes de executar NSGA-II.
6. Gerar Pareto 3D somente após F1/F2/F3 válidos e candidatos factíveis auditados.

## 6. Limites explícitos

- Não foram produzidas soluções científicas, frentes de Pareto, simulações R1–R3 ou resultados de artigo.
- M1 testa estrutura, não veracidade da base, compatibilidade civil nem homologação dos 137 valores.
- O código de M2 é propositalmente mínimo para demonstrar ambiente/solver; não contém BESS, CHP ou recarga individual.
- Nenhum parâmetro pendente foi substituído por zero.
