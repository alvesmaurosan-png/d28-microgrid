# Table of Contents

**Natureza:** documento técnico-científico de especificação controlada. As equações foram convertidas em objetos matemáticos editáveis no Word; as expressões em fonte monoespaçada são preservadas para rastreabilidade. **Não é homologação das entradas pendentes.**

**Critério de precedência proposto (após aprovação formal):** PC-REV08 > Base Mestre PC-REV07 (137 IDs, congelada) > fontes históricas (interpretação) > este documento.

# D28 — Documento Final Consolidado REV03 / PC-REV08 — Especificação matemática e contrato de resultados

**Identificação:** EM-D28-PC-REV08 / REV03, edição de consolidação pré-implementação  
**Referências internas:** PC-REV07; Base Mestre D28 de 137 IDs; Plano Mestre de Formulação; Auditoria de Consistência Matemática (24 achados).  
**Estado:** **CONGELÁVEL COMO ESPECIFICAÇÃO DE ARQUITETURA, NOTAÇÃO, EQUAÇÕES DEFINIDAS E REGRAS DE BLOQUEIO. NÃO HOMOLOGADA COMO MODELO COMPLETO EXECUTÁVEL R0–R3.**  
**Controle:** nenhuma alteração de hipótese ou parâmetro é autorizada por este documento. Campos `PENDENTE` são contratos explícitos, não valores zero.

## 1. Escopo científico, arquiteturas e regras de precedência

O problema possui uma camada externa de **dimensionamento multiobjetivo NSGA-II** e um subproblema interno de **despacho MILP de passo 15 min**. As arquiteturas são R0 (rede/PV/BESS), R1 (CHP com GN físico), R2 (CHP com biogás local e biodigestão) e R3 (CHP com GN físico e atributo CGOB separado). A recarga integral dos ônibus é obrigatória; a importação no PCC é limitada a 2.500 kW e a exportação é nula. Os cenários são E100, E200, E300 em 2026, E375 em 2038 e E450 em 2050. Frota total 450 é **hipótese sintética**.

**Precedência proposta, condicionada à aprovação:** (1) decisão vigente do PC-REV08; (2) valor e unidade da Base Mestre congelada; (3) evidência histórica para interpretação, sem sobrescrita; (4) este documento para definição de equações e verificações. Em caso de conflito, bloquear a avaliação correspondente e registrar decisão; não selecionar valores por conveniência.

**Dois níveis de execução:** - **R0-A, agregado, desenvolvimento:** pode testar balanços, PV/BESS, importação e F2 no horizonte de 70 dias; não demonstra factibilidade individual de recarga, custo anual F1 nem ACV completa F3. - **R0-I/R1-I/R2-I/R3-I, completos:** requerem B01–B06 resolvidos nas partes pertinentes e validação B07. Não converter teste exploratório em resultado científico homologado.

## 2. Notação, conjuntos, índices e unidades

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

## 3. Vetor de dimensionamento e condição de linearidade

**EQ-000 — Decisão externa.** `x=(C_PV,E_B,P_PCS,N_g,P_CHP,escolha_CHP,V_G,escala_digestor,r)` contém somente coordenadas cujo domínio e custo estejam documentados. Variáveis inteiras/categóricas devem usar operadores ou codificação mista explícitos. `x` é **fixado antes** de montar cada MILP. Para R0, `P_CHP=V_G=V_D=0`; R1/R3 não produzem biogás local; R2 incorpora digestão e estoque.

$$\mathbf{x} = \left( C_{PV},E_{B},P_{PCS},N_{g},P_{CHP},V_{G},V_{D},r \right)$$

**Propriedade matemática:** com `x` fixo, produtos `P_CHP·u_h`, `P_PCS·u_h`, `C_PV·φ_h` são coeficientes constantes multiplicados por variáveis binárias/contínuas, logo lineares. Não implementar simultaneamente `x` variável e `u_h` binária sem linearização exata e limites justificados. **Catálogo e domínio CHP ainda não demonstrados:** não inventar capacidades discretas.

**Onde:** x: vetor de dimensionamento externo; C_PV: capacidade fotovoltaica (kWp); E_B: capacidade BESS (kWh); P_PCS: potência do conversor (kW); N_g: número de gabinetes (inteiro); P_CHP: potência nominal CHP (kWe); V_G: armazenamento de gás (Nm³ de estoque, distinguindo volume físico); r: arquitetura. Escolha_CHP e escala_digestor são decisões de domínio ainda condicionado.

## 4. Equações de despacho elétrico e PV

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

## 5. BESS — estado, operação e envelhecimento

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

## 6. CHP, gás natural, biogás e biodigestor

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

## 7. Recarga individual e gabinetes duplos — especificação fechada, dados ainda ausentes

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

## 8. Horizonte temporal, anualização e cenários

**EQ-035 — Dias-tipo e PKM.** `N_úteis=250`, `N_sáb=52`, `N_dom=63`, soma 365. Para um cenário com distribuição documentada: `PKM_s,ano = 23 Σ_d N_d Σ_b km_b,d` passageiros·km/ano. Essa fórmula exige a definição do conjunto de ônibus efetivamente atendidos e da correspondência de dias-tipo. O valor histórico de PKM é **exploratório**, não substitui a construção documentada.

$$PKM_{s,ano} = 23\sum_{d}^{}N_{d}\sum_{b}^{}km_{b,d}$$

**Regra temporal mandatória:** a série de demanda possui 70 dias sintéticos, enquanto a solar 15 min possui 70 dias datados em 2025; igualdade de índices não comprova igualdade de datas. **B01 permanece aberto**. Os cenários 2038 e 2050 não são automaticamente anos consecutivos de um VPL iniciado em 2026; definir experimento por ano de referência ou cronograma de transição explícito antes de F1/F3 definitivos.

**Onde:** PKM_s,ano: serviço anual (passageiros·km); N_d: dias anuais do tipo d (dias/ano); km_b,d: distância percorrida (km/dia); b: ônibus efetivamente atendido; 23: ocupação média (passageiros/ônibus).

## 9. Custos, tarifação e F1

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

## 10. Pico de importação F2

**EQ-041 — F2 (kW).** `F2_s,r(x) = min_{despacho factível} z_s,r` quando o MILP for formulado para minimizar pico, sujeito a `z_s,r ≥ P_grid,h` para todo `h∈H_s`. Se o despacho interno otimizar outra função, o valor relatado é `max_h P_grid,h` da solução escolhida, não o mínimo possível de pico. **O critério de desempate/despacho interno precisa ser explicitamente fixado antes do NSGA-II**; não presumir que a mesma solução minimiza custo e pico. Comparar F2 apenas no mesmo cenário e domínio temporal.

$$F_{2} = \max_{h \in H_{s}}P_{h}^{grid}$$

**Onde:** F2_s,r(x): objetivo de pico da arquitetura r no cenário s para dimensionamento x (kW); z_s,r: variável epigráfica de pico (kW); P_grid,h: importação no PCC (kW); H_s: conjunto de intervalos avaliados. O mínimo depende da função efetivamente otimizada pelo MILP.

## 11. ACV, fronteiras e F3

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

## 12. Exergia complementar

**EQ-046 — Balanço exergético, apenas pós-processamento.** `Ex_in = Ex_useful + Ex_destroyed + Ex_losses` \[kWh de exergia\], sob fronteira e ambiente de referência definidos. Não calcular eficiência exergética ou destruição com `PCI` como se fosse exergia química sem convenção/fator documentado. Exergia não é F4.

$$Ex_{in} = Ex_{useful} + Ex_{destroyed} + Ex_{losses}$$

**Onde:** Ex_in: exergia de entrada; Ex_useful: exergia útil; Ex_destroyed: destruição por irreversibilidades; Ex_losses: perdas para o exterior. Todas as parcelas em kWh de exergia; temperatura/estado de referência ainda requerem especificação.

## 13. Função de avaliação do NSGA-II e contrato do MILP

**ALG-001.** Para cada `(s,r,x)` validado: (i) checar domínios e arquitetura; (ii) fixar `x`; (iii) construir MILP com dados de cenário imutáveis; (iv) resolver com HiGHS; (v) registrar status, gap e tolerâncias; (vi) testar balanços e fronteiras; (vii) rejeitar solução com déficit, violações ou status não aceito; (viii) calcular indicadores disponíveis em módulo independente; (ix) armazenar rastreabilidade de parâmetros, hash, solver e seed. **Não devolver objetivos numéricos falsos para configurações inviáveis.** Para avaliação triobjetiva, exigir F1/F2/F3 completos e comparáveis; até lá, o protótipo pode operar como teste de despacho e, quando justificado, com objetivos parciais claramente separados.

A escolha da função escalar do MILP interno (custo operacional, pico ou combinação lexicográfica) **não está fechada por estas fontes**. Esta é uma decisão matemática material: não impor uma preferência sem registro. Os hiperparâmetros do NSGA-II (população, gerações e seeds) são parâmetros experimentais ainda a definir, não valores físicos a inventar.

## 14. Condições de contorno, teste de conservação e aceite

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

## 15. Rastreabilidade dos 137 parâmetros e controle de versão

O anexo `D28_Especificacao_Rastreabilidade_137_IDs.csv` enumera **todos os 137 IDs** com valor e unidade original, destino matemático principal, estado de uso e colunas reservadas para o nome exato da constraint Pyomo e teste. `META`/`GOV`/`HIST` indicam metadados, governança e registros históricos; não se força sua transformação em coeficiente. O mapeamento é **de especificação**, não uma alegação de que o código existe ou foi validado.

Qualquer mudança futura exige registro de: ID da decisão, motivação, equações afetadas, IDs de parâmetros, testes alterados, impacto na comparabilidade e aprovação. Alterações não aprovadas não entram na branch principal. O PC-REV07 e a Base Mestre permanecem imutáveis.

## 16. Redação científica — estrutura sugerida da Metodologia

1.  **Objeto e cenários:** garagem D28, frota sintética, E100–E450, arquiteturas R0–R3 e fronteiras.
2.  **Dados:** INMET A701/A771, séries solares, demanda REV09, calendário de 70 dias e limitações de pareamento.
3.  **Dimensionamento:** vetor externo NSGA-II, domínios, variáveis discretas e limites geométricos.
4.  **Despacho:** MILP de 15 minutos, balanço AC, PCC, PV, BESS, CHP, biodigestão e recarga dual.
5.  **Objetivos:** VPL custos/VPL PKM (F1), pico importado (F2), ACV energética/PKM (F3); exergia complementar.
6.  **Implementação:** Python, Pyomo, HiGHS, pymoo, controle Git/GitHub e hash das entradas.
7.  **Validação e limitações:** factibilidade física, testes de conservação, sensibilidade, disponibilidade e pendências de ACV/recarga individual.

**Importante:** esta seção é roteiro metodológico; não afirmar que experimentos, sensibilidade, convergência ou validação já foram executados.


## 18. Controle de revisão REV03 e correspondência com PC-REV08

**Situação documental:** especificação técnica REV03, subordinada ao PC-REV08 **proposto**, cuja vigência normativa depende de aprovação formal. A Base Mestre PC-REV07 com 137 IDs continua congelada; esta revisão não altera parâmetros, unidades, equações EQ-000–EQ-046 nem homologa bloqueios pendentes. Preservam-se os significados de F1 (BRL/PKM), F2 (kW) e F3 (kgCO₂e/PKM). A revisão consiste na inclusão de um contrato verificável de resultados, figuras, tabelas e proveniência.

### 18.1. Identificadores e granularidade

Cada execução terá `experiment_id`, `architecture_id` (R0–R3), `scenario_id` (E100/E200/E300/E375/E450), `reference_year` (2026/2038/2050), `run_id`, `seed`, `input_manifest_sha256`, `config_sha256`, `git_commit`, versões do solver e da plataforma, data UTC e estado de validação. Não confundir ano de referência com os 70 dias sintéticos de despacho, seus 6720 intervalos de 15 minutos ou o horizonte econômico de 20 anos. O desenho contempla até 20 células arquitetura × cenário; executar apenas as admissíveis e registrar as exclusões.

### 18.2. Definição operacional da fronteira triobjetiva

A solução candidata é elegível somente se todos os requisitos físicos, temporais, de atendimento da frota e do solver estiverem satisfeitos e os três objetivos forem finitos, rastreáveis e calculados com os mesmos limites de sistema. Para duas soluções elegíveis `a` e `b`, `a` domina `b` se `F_i(a) <= F_i(b)` para todo `i` em {1,2,3} e houver ao menos um objetivo estritamente menor. A fronteira `pareto_3d.csv` reúne as soluções elegíveis não dominadas, segundo tolerâncias numéricas documentadas, sem agregação de objetivos nem descarte arbitrário de extremos. Empates e duplicatas exigem regra determinística registrada.

As projeções F1×F2, F1×F3 e F2×F3 são **projeções da fronteira triobjetiva** e não devem ser rotuladas como frentes recalculadas de dois objetivos. Comparações entre arquiteturas podem representar sobreposição de frentes, mas não autorizam comparar pontos de diferentes anos, perfis de demanda ou denominadores PKM sem explicitar a base comum e as ressalvas.

### 18.3. Contrato de tabelas e arquivos

| Artefato | Conteúdo mínimo | Condição de uso |
|---|---|---|
| `candidates_all.csv` | IDs, vetor de decisão, status, objetivos ou motivo de ausência, seed, geração | Todos os candidatos avaliados |
| `candidates_feasible.csv` | Soluções factíveis, três objetivos, métricas e vínculo com despacho | Após checagem de factibilidade |
| `pareto_3d.csv` | Soluções não dominadas e objetivos F1/F2/F3, unidades e IDs | Somente com F3 validado |
| `convergence.csv` | Geração, avaliações, contagem factível, indicadores e parâmetros do indicador | Não declarar convergência por inspeção visual isolada |
| `dispatch_timeseries.parquet` | Série temporal, solução, dia, passo, potências, SOC, importação e estados pertinentes | Checagem energética e reprodução |
| `figures_manifest.csv` | ID da figura, tipo, fonte, hash, filtros, código, versão, status | Obrigatório para cada figura |
| `manifest.json` | Configuração, fontes, hashes, software, seed, bloqueios, validação e escopo | Obrigatório por execução |

Tabelas científicas mínimas: matriz de experimentos e admissibilidade; parâmetros e premissas com proveniência; desempenho da otimização e factibilidade; métricas das soluções representativas; comparações R0–R3 por cenário/ano; sensibilidade e limitações, quando aplicáveis. Resultados monetários primários em BRL e conversões internacionais com câmbio, data e método documentados.

### 18.4. Contrato de figuras

Por célula admissível, produzir, quando os dados forem elegíveis: (i) Pareto F1–F2–F3 tridimensional; (ii) projeções F1×F2, F1×F3 e F2×F3; (iii) convergência/qualidade e diversidade, com definição do indicador; (iv) dispersão dos dimensionamentos; (v) perfis de despacho para soluções representativas e extremos de cada objetivo. Para comparações, padronizar escalas e unidades e distinguir arquiteturas, cenários e anos. Toda legenda deve identificar estado do resultado, critérios de seleção e execução de origem. Publicar figuras em formato vetorial (`.svg` ou `.pdf`) e, quando necessário, `.png` de alta resolução, mantendo código e dados de origem.

### 18.5. Bloqueio de publicação triobjetiva

Enquanto fatores de ACV necessários, inclusive D11-014, D11-015, D11-016, D11-018 e D11-019, ou quaisquer outros requisitos de F3 estiverem abertos, **não** gerar ou identificar `pareto_3d.csv` e figuras F1–F2–F3 como definitivos. É permitido diagnóstico exploratório claramente identificado, sem imputação zero para ausências e sem equipará-lo a resultado científico validado. A factibilidade por ônibus depende do fechamento de B02; a representação agregada não a substitui.

### 18.6. Estrutura vinculante do repositório

```text
src/d28/reporting/pareto.py
src/d28/reporting/figures.py
scripts/export_pareto.py
scripts/build_figures.py
results/<experiment_id>/<architecture_id>/<scenario_id>/<run_id>/
  manifest.json
  candidates_all.csv
  candidates_feasible.csv
  pareto_3d.csv                 # somente quando F3 elegível
  convergence.csv
  dispatch_timeseries.parquet
  projections/
  figures/3d/
  figures/projections/
  figures/dispatch/
  figures/comparisons/
  figures_manifest.csv
reports/figures_publication/
reports/tables_publication/
tests/reporting/
```

### 18.7. Critérios de aceitação e auditoria

**V01** consistência entre IDs de execução, arquitetura, cenário e ano; **V02** integridade dos hashes e versões; **V03** reconciliação entre candidatos e factíveis; **V04** verificação independente da não dominância com tolerâncias; **V05** três objetivos finitos, unidades e denominadores consistentes; **V06** rastreabilidade figura→CSV→solução→despacho→entrada; **V07** reexecução determinística das figuras; **V08** verificação de balanços e limites; **V09** comparação apenas sob bases explicitamente compatíveis; **V10** bloqueio de resultados finais com B01–B07 pertinentes abertos. Nenhum teste isolado substitui aprovação científica.

### 18.8. Histórico desta revisão

| Revisão | Natureza | Efeito |
|---|---|---|
| REV02 / PC-REV07 | Notações e explicações das equações | Linha de base matemática preservada |
| **REV03 / PC-REV08** | Contrato de resultados, Pareto, repositório, validação e governança | Acréscimo documental; sem alteração matemática ou homologação |


## 17. Parecer de consolidação

A presente especificação **corrige os 24 achados no nível de definição, classificação de lacunas ou imposição de teste**, sem alterar os 137 valores e sem criar hipóteses. O núcleo agregado pode ser programado. A formulação R0–R3 completa permanece **condicionada** a dados e decisões já identificados em B01–B07. Congelar este documento como **baseline de implementação controlada**, não como certificação de modelo científico concluído.

# ANEXO A — Plano operacional de implementação (fonte consolidada)

## 2. Contrato de projeto antes da primeira linha do otimizador

    d28-microgrid/
      README.md  pyproject.toml  .gitignore  .python-version
      config/                 # parâmetros de execução; nenhum valor físico inventado
      data/raw/               # cópias imutáveis das entradas aprovadas
      data/processed/         # dados derivados, com proveniência
      docs/protocolo/         # PC-REV07, controle de versões
      docs/metodologia/       # esta formulação, dicionário de variáveis, hipóteses
      docs/decisoes.md        # registro de mudança, motivação e aprovação
      src/d28/io/             # ingestão, schemas, unidades, checksums
      src/d28/scenarios/      # dias-tipo, cenários, janelas, perfis
      src/d28/models/         # PV, BESS, CHP, combustível, carregadores, rede
      src/d28/dispatch/       # MILP Pyomo
      src/d28/objectives/     # F1/F2/F3 com auditoria independente
      src/d28/optimization/   # NSGA-II pymoo e tratamento de inviabilidade
      src/d28/reporting/      # CSV/JSON, gráficos, tabelas do artigo
      tests/unit/  tests/integration/  tests/physics/  tests/regression/
      experiments/            # configurações versionadas; seeds
      results/                # resultados gerados, não commitados por padrão

Recomendação técnica de bibliotecas: Python 3.11 ou 3.12 fixado, pandas, numpy, openpyxl, pydantic, pyomo, highspy, pymoo, pytest, scipy e matplotlib; travar versões exatas em lockfile após o primeiro teste de instalação. GitHub Actions roda testes sem dados confidenciais. Nenhuma dependência da edição Professional do PyCharm.

## 7. Arquitetura de avaliação NSGA-II → MILP

1.  Ler e validar o genoma misto, domínios e arquitetura R0–R3.
2.  Construir configuração física; rejeitar imediatamente violação de limites geométricos e domínios.
3.  Para cada cenário e dia/horizonte exigido, montar MILP com parâmetros imutáveis e resolver com HiGHS.
4.  Verificar status ótimo/factível, tolerâncias, balanços e energia não atendida. Se inviável, registrar motivo e vetor de violação; **não produzir F1/F2/F3 falsamente válidos**.
5.  Para configuração factível, calcular objetivos em módulo independente do MILP, usando fluxos e fatores com proveniência.
6.  Cachear avaliações por hash do vetor, versão de dados, configuração, solver e modelo.
7.  Registrar seed, população, gerações, operadores de variáveis mistas, orçamento de avaliações, tolerâncias, timeout e logs. O PC-REV07 não autoriza inventar valores definitivos desses hiperparâmetros: fixá-los em protocolo experimental antes de rodar.

## 8. Gates de desenvolvimento que impedem retrabalho

| Gate | Entrega obrigatória                                  | Teste de aceitação                                                                |
|------|------------------------------------------------------|-----------------------------------------------------------------------------------|
| M0   | especificação congelada, IDs de equação e dicionário | nenhuma variável/equação sem unidade e fonte; pendências explicitadas             |
| M1   | ingestão e schemas                                   | 137 IDs únicos, arquivos SHA-256, 5×6720 intervalos, sem NaN não permitido        |
| M2   | MILP de balanço agregado R0                          | conservação em cada t, PCC ≤ 2500, PV limitada, BESS física                       |
| M3   | MILP R1/R2/R3                                        | balanços de combustível, CHP e restrições por arquitetura                         |
| M4   | recarga individual                                   | só após B02: janelas, SOC, gabinetes, continuidade e 100% atendimento             |
| M5   | F1/F2/F3                                             | F1/F2 independentes; F3 apenas se fronteira ACV fechada ou explicitamente parcial |
| M6   | NSGA-II                                              | determinismo por seed, tratamento de inviáveis, repetição, convergência           |
| M7   | publicação científica                                | tabelas auditáveis, incerteza, fronteira ACV, versões e limites declarados        |

**Política de bloqueios:** B01 e B02 abertos permitem desenvolvimento de M1–M3 sob recorte sintético agregado, mas não M4 nem inferência operacional individual; B03 e B04 impedem conclusões tarifárias/ACV definitivas; B05/B06 exigem mapeamento final para M5; B07 é validado progressivamente por M1–M6.

## 9. Testes de regressão e casos mínimos

- Um intervalo sem PV/CHP/BESS: `P_grid = carga`; acima de 2500 kW deve ser inviável.
- PV excedente sem exportação: excedente obrigatoriamente cortado ou armazenado.
- BESS em SOC mínimo não descarrega; em máximo não carrega; carga/descarga simultâneas impossíveis.
- CHP desligado gera 0; ligado respeita mínimo de 50%; arquitetura R0 proíbe combustível.
- R2 conserva massa de gás, não consome mais do que estoque e produção; auxiliares não são duplicados.
- Ônibus indisponível não carrega; saída sem 95% SOC torna caso inviável; dois conectores não duplicam potência de gabinete.
- `Σ_t P_t Δt` confere com kWh; 70 dias não são tratados como 365 dias sem pesos documentados.
- F1 testa VPL com exemplo manual; F2 testa máximo sobre intervalo; F3 falha explicitamente se inventário incompleto.
- Repetir seed+versões gera mesmos resultados dentro de tolerâncias do solver.

## 10. GitHub e reprodutibilidade

- Commits por gate M0–M7; tags `m0-spec`, `m1-ingestao`, etc.; branches curtas e pull requests com checklist científico.
- `.gitignore` para `.venv/`, caches, credenciais, resultados volumosos, arquivos temporários. Publicar dados brutos somente após verificar licença, privacidade e tamanho; caso contrário disponibilizar checksums e instruções de obtenção.
- `README.md` com Python, instalação, execução dos testes, execução de experimento, limitações B01–B07, tabela de variáveis e citação sugerida.
- Toda saída deve incluir `run_manifest.json` (hash das entradas, commit Git, Python, dependências, solver, seeds, parâmetros, data e duração), `dispatch.csv`, `objectives.csv`, `feasibility.json` e registro de mensagens do solver.
- Um notebook de artigo pode **ler** resultados; não deve conter lógica paralela não testada do modelo.

## 11. Estrutura pronta para a Metodologia do artigo

1.  Objeto e fronteira do sistema; garagem D28 como caso sintético, não inventário de frota real.
2.  Cenários, perfis operacionais, dias-tipo e fontes de dados.
3.  Arquiteturas R0–R3 e representação tecnológica.
4.  Formulação do problema: índices, parâmetros, variáveis e EQ-001–EQ-017.
5.  Acoplamento NSGA-II/MILP, tratamento de inviabilidade, parâmetros experimentais.
6.  Fronteiras econômicas e ambientais de F1–F3; exclusões e dados condicionais.
7.  Verificação física, validação de software, sensibilidade, convergência e replicação.
8.  Limitações B01–B07 e critérios de interpretação de resultados.

## 12. Decisões que **não** podem ser silenciosamente preenchidas pelo programador

- Pareamento civil dos 70 dias solares e de demanda (B01); existência de série anual 15-min validada.
- Matriz ônibus × disponibilidade × SOC × viagens, e sua compatibilidade com a demanda REV09 (B02).
- Seleção da estrutura tarifária efetiva D05-003/004 e regra de faturamento ponta/demanda (B03).
- Inventários e fronteiras ACV completos D11-013/017 e demais fatores (B04).
- Catálogo e domínios discretos CHP, rampas, armazenamento de gás, perdas e produção temporal (B05).
- Anualização dos 70 dias, pesos de dias-tipo e PKM definitivo por cenário/ano (B06).
- Critérios de tolerância, timeouts, política de infeasibilidade e teste de integração solver (B07).

**Regra de encerramento:** só alterar a especificação quando houver erro demonstrável ou decisão científica formal; qualquer mudança após M0 recebe registro de impacto nas equações, testes, resultados e artigo. Este documento é o plano mestre pré-implementação, não substitui o PC-REV07.


## Nota de harmonização documental — 18/10/2026 (controle de mudanças)

Esta nota registra correções de referências cruzadas e **não** constitui aprovação do PC-REV08 nem modificação de parâmetros ou equações. O PC-REV08 é a referência metodológica **proposta**; a Base Mestre PC-REV07 de 137 IDs permanece congelada. Menções históricas ao PC-REV07 continuam válidas como identificação de origem. A implementação atual usa `src/d28/reporting/plots.py` e `src/d28/reporting/pareto.py`; o exemplo antigo `reporting.py` não é uma API vigente. O protótipo M2 é exclusivamente agregado, sintético e reduzido. B01–B07 e a definição de escalarização do MILP continuam abertos conforme auditoria. Tolerâncias científicas de dominância e repetibilidade exigem decisão antes de M6/M7.
