# D28 - Dossie de Auditoria da Formulacao R0

Documento de inspecao estatica.
Nao representa homologacao cientifica.

## CODIGO: .internal_review/src/d28/dispatch/milp.py

0001 | """M2: protótipo R0 agregado, explicitamente NÃO científico."""
0002 | def build_r0_smoke(load_kw, pv_pu, pv_capacity_kw, pcc_cap_kw=2500.0):
0003 |     import pyomo.environ as p
0004 |     if len(load_kw)!=len(pv_pu) or not load_kw:raise ValueError('Séries inválidas')
0005 |     m=p.ConcreteModel();m.T=p.RangeSet(0,len(load_kw)-1)
0006 |     m.grid=p.Var(m.T,domain=p.NonNegativeReals,bounds=(0,pcc_cap_kw))
0007 |     m.pv=p.Var(m.T,domain=p.NonNegativeReals)
0008 |     m.pv_cap=p.Constraint(m.T,rule=lambda m,t:m.pv[t]<=pv_capacity_kw*float(pv_pu[t]))
0009 |     m.balance=p.Constraint(m.T,rule=lambda m,t:m.grid[t]+m.pv[t]==float(load_kw[t]))
0010 |     m.obj=p.Objective(expr=sum(m.grid[t] for t in m.T),sense=p.minimize)
0011 |     return m
0012 | 
0013 | def build_r0_milp(
0014 |     load_kw,
0015 |     pv_pu,
0016 |     pv_capacity_kw,
0017 |     bess_capacity_kwh,
0018 |     pcs_power_kw,
0019 |     *,
0020 |     soh=1.0,
0021 |     pcc_cap_kw=2500.0,
0022 |     dt_hours=0.25,
0023 |     eta_charge=0.922,
0024 |     eta_discharge=0.922,
0025 |     initial_soc=0.50,
0026 |     terminal_policy="free",
0027 |     terminal_energy_kwh=None,
0028 |     pv_capacity_max_kwp=None,
0029 | ):
0030 |     """Constrói MILP R0 agregado sintético (EQ-001 a EQ-010, escopo PV+BESS).
0031 | 
0032 |     load_kw representa a demanda AC total, sem dupla contagem de recarga.
0033 |     pv_pu é uma série específica previamente validada (kW/kWp); não se
0034 |     aplica fator de geração adicional. Sem CHP, exportação ou déficit.
0035 | 
0036 |     terminal_policy: 'free', 'cyclic' ou 'fixed'. A opção 'cyclic' só pode
0037 |     ser escolhida se o horizonte justificar fechamento cíclico (EQ-009).
0038 |     SOH é exógeno; política de reposição não é inferida (EQ-010).
0039 |     """
0040 |     import math
0041 |     import pyomo.environ as p
0042 | 
0043 |     try:
0044 |         loads = [float(x) for x in load_kw]
0045 |         solar = [float(x) for x in pv_pu]
0046 |     except (TypeError, ValueError) as exc:
0047 |         raise ValueError("Séries de demanda e PV devem ser numéricas") from exc
0048 |     if not loads or len(loads) != len(solar):
0049 |         raise ValueError("Séries vazias ou com comprimentos diferentes")
0050 |     if not all(math.isfinite(x) and x >= 0 for x in loads + solar):
0051 |         raise ValueError("Séries devem ser finitas e não negativas")
0052 | 
0053 |     values = {
0054 |         "pv_capacity_kw": pv_capacity_kw,
0055 |         "bess_capacity_kwh": bess_capacity_kwh,
0056 |         "pcs_power_kw": pcs_power_kw,
0057 |         "soh": soh,
0058 |         "pcc_cap_kw": pcc_cap_kw,
0059 |         "dt_hours": dt_hours,
0060 |         "eta_charge": eta_charge,
0061 |         "eta_discharge": eta_discharge,
0062 |         "initial_soc": initial_soc,
0063 |     }
0064 |     if pv_capacity_max_kwp is not None:
0065 |         values["pv_capacity_max_kwp"] = pv_capacity_max_kwp
0066 |     try:
0067 |         values = {key: float(value) for key, value in values.items()}
0068 |     except (TypeError, ValueError) as exc:
0069 |         raise ValueError("Parâmetros numéricos inválidos") from exc
0070 |     if not all(math.isfinite(v) for v in values.values()):
0071 |         raise ValueError("Parâmetros devem ser finitos")
0072 |     pv_capacity_kw = values["pv_capacity_kw"]
0073 |     bess_capacity_kwh = values["bess_capacity_kwh"]
0074 |     pcs_power_kw = values["pcs_power_kw"]
0075 |     soh = values["soh"]
0076 |     pcc_cap_kw = values["pcc_cap_kw"]
0077 |     dt_hours = values["dt_hours"]
0078 |     eta_charge = values["eta_charge"]
0079 |     eta_discharge = values["eta_discharge"]
0080 |     initial_soc = values["initial_soc"]
0081 |     if min(pv_capacity_kw, bess_capacity_kwh, pcs_power_kw, pcc_cap_kw) < 0:
0082 |         raise ValueError("Capacidades e PCC não podem ser negativos")
0083 |     if not (0 < soh <= 1):
0084 |         raise ValueError("SOH deve estar em (0, 1]")
0085 |     if dt_hours <= 0:
0086 |         raise ValueError("dt_hours deve ser positivo")
0087 |     if not (0 < eta_charge <= 1 and 0 < eta_discharge <= 1):
0088 |         raise ValueError("Eficiências devem estar em (0, 1]")
0089 |     if not (0.10 <= initial_soc <= 0.90):
0090 |         raise ValueError("SOC inicial deve estar em [0.10, 0.90]")
0091 |     if pcs_power_kw > 0.55 * bess_capacity_kwh + 1e-9:
0092 |         raise ValueError("PCS excede 0,55 da capacidade BESS (EQ-008)")
0093 |     if pv_capacity_max_kwp is not None and pv_capacity_kw > values["pv_capacity_max_kwp"] + 1e-9:
0094 |         raise ValueError("Capacidade FV excede teto geométrico informado")
0095 |     if pv_capacity_max_kwp is not None and values["pv_capacity_max_kwp"] < 0:
0096 |         raise ValueError("Teto geométrico inválido")
0097 |     if terminal_policy not in ("free", "cyclic", "fixed"):
0098 |         raise ValueError("terminal_policy deve ser free, cyclic ou fixed")
0099 |     if terminal_policy == "fixed":
0100 |         if terminal_energy_kwh is None:
0101 |             raise ValueError("fixed requer terminal_energy_kwh")
0102 |         try:
0103 |             terminal_energy_kwh = float(terminal_energy_kwh)
0104 |         except (TypeError, ValueError) as exc:
0105 |             raise ValueError("Energia terminal inválida") from exc
0106 |         if not math.isfinite(terminal_energy_kwh) or not (
0107 |             0.10 * bess_capacity_kwh * soh - 1e-9 <= terminal_energy_kwh
0108 |             <= 0.90 * bess_capacity_kwh * soh + 1e-9
0109 |         ):
0110 |             raise ValueError("Energia terminal fora da faixa SOC")
0111 |     elif terminal_energy_kwh is not None:
0112 |         raise ValueError("terminal_energy_kwh só é permitido com terminal_policy='fixed'")
0113 | 
0114 |     n = len(loads)
0115 |     capacity_usable = bess_capacity_kwh * soh
0116 |     m = p.ConcreteModel(name="R0_PV_BESS_synthetic")
0117 |     m.T = p.RangeSet(0, n - 1)
0118 |     m.S = p.RangeSet(0, n)  # estados incluem o instante terminal
0119 |     m.load_kw = p.Param(m.T, initialize=dict(enumerate(loads)))
0120 |     m.pv_pu = p.Param(m.T, initialize=dict(enumerate(solar)))
0121 |     m.grid = p.Var(m.T, domain=p.NonNegativeReals, bounds=(0, pcc_cap_kw))
0122 |     m.pv = p.Var(m.T, domain=p.NonNegativeReals)
0123 |     m.pv_curt = p.Var(m.T, domain=p.NonNegativeReals)
0124 |     m.bess_charge = p.Var(m.T, domain=p.NonNegativeReals)
0125 |     m.bess_discharge = p.Var(m.T, domain=p.NonNegativeReals)
0126 |     m.bess_mode = p.Var(m.T, domain=p.Binary)
0127 |     m.bess_energy = p.Var(m.S, domain=p.NonNegativeReals,
0128 |                           bounds=(0.10 * capacity_usable, 0.90 * capacity_usable))
0129 | 
0130 |     m.balance = p.Constraint(
0131 |         m.T,
0132 |         rule=lambda m, t: m.grid[t] + m.pv[t] + m.bess_discharge[t]
0133 |         == m.load_kw[t] + m.bess_charge[t],
0134 |     )
0135 |     m.pv_accounting = p.Constraint(
0136 |         m.T, rule=lambda m, t: m.pv[t] + m.pv_curt[t] == pv_capacity_kw * m.pv_pu[t]
0137 |     )
0138 |     m.bess_energy_balance = p.Constraint(
0139 |         m.T,
0140 |         rule=lambda m, t: m.bess_energy[t + 1]
0141 |         == m.bess_energy[t]
0142 |         + eta_charge * m.bess_charge[t] * dt_hours
0143 |         - m.bess_discharge[t] * dt_hours / eta_discharge,
0144 |     )
0145 |     m.bess_charge_limit = p.Constraint(
0146 |         m.T, rule=lambda m, t: m.bess_charge[t] <= pcs_power_kw * m.bess_mode[t]
0147 |     )
0148 |     m.bess_discharge_limit = p.Constraint(
0149 |         m.T, rule=lambda m, t: m.bess_discharge[t] <= pcs_power_kw * (1 - m.bess_mode[t])
0150 |     )
0151 |     m.bess_initial = p.Constraint(expr=m.bess_energy[0] == initial_soc * capacity_usable)
0152 |     if terminal_policy == "cyclic":
0153 |         m.bess_terminal = p.Constraint(expr=m.bess_energy[n] == m.bess_energy[0])
0154 |     elif terminal_policy == "fixed":
0155 |         m.bess_terminal = p.Constraint(expr=m.bess_energy[n] == terminal_energy_kwh)
0156 |     # Objetivo operacional provisório: energia importada [kWh].
0157 |     m.obj = p.Objective(expr=dt_hours * sum(m.grid[t] for t in m.T), sense=p.minimize)
0158 |     m._r0_metadata = {
0159 |         "scientific_validation": False,
0160 |         "dt_hours": dt_hours,
0161 |         "soh": soh,
0162 |         "terminal_policy": terminal_policy,
0163 |         "scope": "synthetic_aggregate_PV_BESS_no_CHP",
0164 |     }
0165 |     return m

## CODIGO: .internal_review/src/d28/optimization/nsga2.py

0001 | """M6: integração bloqueada até validação do despacho, indicadores e método interno."""
0002 | def run_scientific_nsga2(*args,**kwargs):
0003 |     raise RuntimeError('BLOQUEADO: M2–M5 e decisão de objetivo interno do MILP pendentes; sem otimização triobjetiva científica')

## CODIGO: .internal_review/tests/physics/test_r0_milp.py

0001 | """Testes físicos sintéticos R0; não homologam as entradas D28."""
0002 | import pytest
0003 | 
0004 | p = pytest.importorskip("pyomo.environ")
0005 | from d28.dispatch.milp import build_r0_milp, build_r0_smoke
0006 | 
0007 | 
0008 | def solve(model):
0009 |     solver = p.SolverFactory("appsi_highs")
0010 |     if not solver.available():
0011 |         pytest.skip("HiGHS indisponível")
0012 |     result = solver.solve(model, load_solutions=False)
0013 |     assert result.solver.termination_condition == p.TerminationCondition.optimal
0014 |     model.solutions.load_from(result)
0015 |     return model
0016 | 
0017 | 
0018 | def test_legacy_smoke_preserved():
0019 |     model = build_r0_smoke([100., 150.], [0., 0.5], 100.)
0020 |     solve(model)
0021 |     assert p.value(model.grid[0]) == pytest.approx(100)
0022 |     assert p.value(model.grid[1]) == pytest.approx(100)
0023 | 
0024 | 
0025 | def test_r0_balance_pv_curtailment_and_pcc():
0026 |     model = solve(build_r0_milp([10., 50., 20.], [0., 1., 0.5], 100., 0., 0.))
0027 |     for t in model.T:
0028 |         assert p.value(model.grid[t] + model.pv[t] + model.bess_discharge[t]
0029 |                        - model.load_kw[t] - model.bess_charge[t]) == pytest.approx(0, abs=1e-7)
0030 |         assert p.value(model.pv[t] + model.pv_curt[t]) == pytest.approx(
0031 |             100 * p.value(model.pv_pu[t]), abs=1e-7
0032 |         )
0033 |         assert 0 <= p.value(model.grid[t]) <= 2500
0034 |     assert p.value(model.pv_curt[1]) == pytest.approx(50, abs=1e-7)
0035 |     assert p.value(model.obj) == pytest.approx(2.5, abs=1e-7)
0036 | 
0037 | 
0038 | def test_bess_physics_and_cyclic_terminal():
0039 |     model = solve(build_r0_milp(
0040 |         [80., 160., 80., 160.], [0., 0., 0., 0.], 0.,
0041 |         200., 100., terminal_policy="cyclic", pcc_cap_kw=2500.
0042 |     ))
0043 |     assert p.value(model.bess_energy[0]) == pytest.approx(100)
0044 |     assert p.value(model.bess_energy[4]) == pytest.approx(100)
0045 |     for t in model.T:
0046 |         charge = p.value(model.bess_charge[t])
0047 |         discharge = p.value(model.bess_discharge[t])
0048 |         mode = p.value(model.bess_mode[t])
0049 |         assert charge <= 100 * mode + 1e-7
0050 |         assert discharge <= 100 * (1 - mode) + 1e-7
0051 |         assert charge * discharge == pytest.approx(0, abs=1e-7)
0052 |         assert p.value(model.bess_energy[t + 1]) == pytest.approx(
0053 |             p.value(model.bess_energy[t]) + 0.922 * charge * 0.25
0054 |             - discharge * 0.25 / 0.922, abs=1e-7
0055 |         )
0056 |     for s in model.S:
0057 |         assert 20 - 1e-7 <= p.value(model.bess_energy[s]) <= 180 + 1e-7
0058 | 
0059 | 
0060 | def test_soh_limits_and_terminal_fixed():
0061 |     model = solve(build_r0_milp(
0062 |         [0.], [0.], 0., 100., 50., soh=0.8,
0063 |         terminal_policy="fixed", terminal_energy_kwh=40.
0064 |     ))
0065 |     assert p.value(model.bess_energy[0]) == pytest.approx(40)
0066 |     assert p.value(model.bess_energy[1]) == pytest.approx(40)
0067 |     assert model.bess_energy[1].ub == pytest.approx(72)
0068 |     assert model.bess_energy[1].lb == pytest.approx(8)
0069 | 
0070 | 
0071 | def test_pcc_infeasible_without_slack():
0072 |     model = build_r0_milp([2600.], [0.], 0., 0., 0.)
0073 |     solver = p.SolverFactory("appsi_highs")
0074 |     if not solver.available():
0075 |         pytest.skip("HiGHS indisponível")
0076 |     # O solver pode lançar exceção ao tentar carregar solução inviável.
0077 |     result = solver.solve(model, load_solutions=False)
0078 |     assert result.solver.termination_condition == p.TerminationCondition.infeasible
0079 | 
0080 | 
0081 | @pytest.mark.parametrize("kwargs", [
0082 |     {"pcs_power_kw": 60.},
0083 |     {"soh": 0.},
0084 |     {"terminal_policy": "unknown"},
0085 |     {"terminal_policy": "fixed"},
0086 |     {"pv_capacity_max_kwp": 10.},
0087 | ])
0088 | def test_invalid_parameters(kwargs):
0089 |     params = dict(load_kw=[10.], pv_pu=[0.], pv_capacity_kw=20.,
0090 |                   bess_capacity_kwh=100., pcs_power_kw=50.)
0091 |     params.update(kwargs)
0092 |     with pytest.raises(ValueError):
0093 |         build_r0_milp(**params)

## DOCUMENTO: docs/methodology/source_protocol/PC_REV08_Protocolo_Cientifico_Tecnico_Consolidado.md

...
0046 | 
0047 | ## 3. Objeto, fronteiras e perguntas científicas
0048 | 
0049 | Estudar a capacidade de alternativas tecnológicas de atender integralmente à recarga elétrica de uma frota sintética em garagem de ônibus sob limite de importação no PCC, minimizando custo normalizado, pico de importação e emissões de ciclo de vida do sistema energético. O inventário energético exclui a fabricação e descarte dos ônibus, conforme fronteira explicitada no modelo. O modelo distingue dimensionamento, despacho, avaliação de objetivos e apresentação de resultados.
0050 | 
0051 | As análises são contrafactuais, não certificam frota real ou configuração física instalada da D28. O resultado científico exige declaração da fronteira, ano de referência, período operacional, horizonte financeiro, fonte de dados, nível de factibilidade e bloqueios.
0052 | 
0053 | ## 4. Cenários, horizontes e arquiteturas
...
0062 | 
0063 | | Arquitetura | Componentes distintivos | Restrição de interpretação |
0064 | |---|---|---|
0065 | | R0 | Rede, PV, BESS e recarga | Protótipo agregado não comprova recarga individual |
0066 | | R1 | R0 + CHP alimentado por GN físico | Combustível e emissões do GN contabilizados |
0067 | | R2 | R0 + CHP a biogás local, biodigestor e gasômetro | Produção, estoque, substrato e emissões modelados |
0068 | | R3 | R0 + CHP com GN físico e atributo CGOB | CGOB contábil separado do gás fisicamente consumido |
0069 | 
0070 | A matriz principal contém **até 20 combinações arquitetura × cenário**, não 60: os anos 2026/2038/2050 já estão associados aos cenários. O horizonte cronológico de despacho, o ano de referência e o horizonte econômico de 20 anos são eixos conceituais distintos. O passo operacional é de 15 min; as séries de 70 dias/6.720 intervalos não são automaticamente anuais. Uma análise de horizonte alternativo exige `temporal_scope_id` explícito e dados admissíveis.
0071 | 
0072 | ## 5. Base Mestre, dados, evidências e proveniência
...
0085 | 
0086 | O NSGA-II propõe capacidades admissíveis; o Pyomo/HiGHS resolve despacho MILP para cada candidato com `x` fixo; verificadores independentes auditam conservação, limites e status; só então as funções objetivo são calculadas. O critério escalar do MILP interno (custo, pico ou prioridade lexicográfica) permanece decisão metodológica pendente, que deve ser fixada antes de comparações. Uma solução não pode ser declarada ótima simultaneamente para três objetivos apenas porque seu despacho interno foi otimizado para um deles.
0087 | 
0088 | Candidatos inviáveis não recebem objetivos fictícios. Registrar causa, status, gap, tolerância, restrições violadas, parâmetros, hash e seed. Um protótipo R0 agregado é etapa de desenvolvimento e não resultado triobjetivo homologado. Não iniciar execuções definitivas com hiperparâmetros evolutivos arbitrários ou sem orçamento e repetibilidade aprovados.
0089 | 
0090 | ## 8. Fronteiras econômicas, ambientais e exergia
0091 | 
0092 | - **F1 [BRL constantes 2026/PKM]:** valor presente dos custos do sistema energético dividido pelo valor presente do serviço de passageiros·km, com taxa real e horizonte coerentes; não anualizar 70 dias automaticamente.
0093 | - **F2 [kW]:** pico de importação no PCC no domínio temporal avaliado, com a convenção de despacho interno expressamente fixada.
0094 | - **F3 [kgCO₂e/PKM]:** emissões de ciclo de vida do sistema energético divididas pelo serviço na mesma fronteira temporal; não somar fatores de rede operacional e ACV total incompatíveis; não omitir fatores ausentes.
0095 | - **Exergia:** pós-processamento complementar, sem criar F4 ou misturar PCI e exergia química sem convenção.
0096 | 
0097 | Os fatores D11-014/015/016/018/019 permanecem pendentes para F3 completa; outras lacunas podem bloquear F1 ou comparabilidade. A moeda de cálculo é BRL2026; conversões para USD, se necessárias, são relatórios comparativos documentados, não parâmetros físicos substitutivos.
0098 | 
0099 | ## 9. Plano experimental e comparabilidade
0100 | 
0101 | Definir antes da execução: `experiment_id`, cenários e arquiteturas elegíveis, `temporal_scope_id`, fronteira de serviço e de ACV, versão da Base Mestre, seed(s), população, gerações, operadores de variáveis mistas, tolerâncias, limite de tempo, tratamento de inviabilidade, função interna do MILP e normalização dos indicadores de comparação. Comparar arquiteturas sob orçamento e condições equivalentes; não atribuir causalidade exclusiva ao tempo quando mudam simultaneamente ano e proporção BEV. A análise de sensibilidade exige experimentos rotulados e não altera silenciosamente o caso-base.
...
0106 | 
0107 | ## 11. Matriz de experimentos e identificação inequívoca
0108 | 
0109 | Executar e identificar separadamente as arquiteturas R0 (rede/PV/BESS), R1 (CHP a gás natural físico), R2 (CHP a biogás local) e R3 (CHP a gás natural físico com atributo CGOB contabilizado separadamente). Os cenários vigentes são E100, E200, E300 (ano de referência 2026), E375 (2038) e E450 (2050). A matriz primária é de até 4 × 5 = 20 combinações arquitetura–cenário, sujeitas à admissibilidade e aos bloqueios. Não tratar automaticamente 2026, 2038 e 2050 como três horizontes adicionais para cada cenário.
0110 | 
0111 | Cada execução deve conter scenario_id, architecture_id, reference_year, temporal_scope_id, economic_horizon_years, experiment_id, run_id e model_version. O horizonte operacional (série cronológica efetivamente modelada), o ano de referência do cenário e o horizonte econômico de 20 anos são dimensões distintas. Comparações só serão admitidas quando as bases temporal, monetária, ambiental e de mobilidade forem compatíveis.
0112 | 
0113 | ## 12. Objetivos, unidades e elegibilidade das fronteiras
0114 | 
0115 | F1 = VPL dos custos do sistema energético / VPL dos passageiros·km [BRL2026/PKM]; F2 = máximo de importação no PCC no domínio temporal da avaliação [kW]; F3 = emissões de ciclo de vida do sistema energético / passageiros·km [kgCO₂e/PKM]. Todos os objetivos são minimizados. A escolha da função escalar do MILP interno e a convenção de avaliação de F2 devem ser fixadas antes da execução, conforme especificação matemática.
0116 | 
0117 | Fronteira de Pareto tridimensional F1–F2–F3: produzir somente quando F1, F2 e F3 estiverem completos, auditados e calculados sob a mesma fronteira e com soluções fisicamente factíveis. Enquanto B04 ou outros bloqueios relevantes persistirem, rotular resultados como “parciais/exploratórios”; permitir projeções ou fronteiras parciais F1–F2 somente quando ambos forem válidos, sem chamá-las de fronteira triobjetiva. Não preencher F3 ausente com zero, estimativa não homologada ou penalidade.
0118 | 
0119 | Uma solução será elegível para a frente publicada somente se satisfizer as restrições físicas, temporais e documentais do experimento, com status do solver e tolerâncias aceitos. Soluções inviáveis, não convergidas ou com indicadores incompletos permanecem em arquivos de auditoria, não na frente válida.
0120 | 
0121 | ## 13. Conjunto mínimo de figuras por combinação admissível
0122 | 
0123 | FIG-P01: diagrama de dispersão 3D F1 × F2 × F3, com eixos e unidades, destaque dos pontos não dominados e legenda da arquitetura/cenário/horizonte. FIG-P02: projeção F1 × F2; FIG-P03: projeção F1 × F3; FIG-P04: projeção F2 × F3. As projeções de uma frente 3D são visualizações da frente triobjetiva e NÃO devem ser apresentadas automaticamente como frentes de Pareto ótimas no plano projetado.
0124 | 
0125 | FIG-P05: evolução da busca por geração (número de soluções factíveis, tamanho da frente, indicador de convergência quando homologado); FIG-P06: distribuição das variáveis de dimensionamento das soluções não dominadas, quando aplicável; FIG-P07: perfis de despacho de soluções representativas, com PCC, PV, BESS, CHP, demanda e demais fluxos pertinentes. Produzir somente gráficos cujos dados e fronteiras estejam validados.
0126 | 
0127 | As figuras deverão conter identificador único, título científico, unidade em cada eixo, legenda, referência temporal, identificação da arquitetura, cenário e versão do modelo, data de execução, descrição de filtros e fonte dos dados. Exportar em PNG (mínimo 300 dpi) e SVG ou PDF vetorial quando tecnicamente aplicável. Preservar código e dados geradores de cada figura.
0128 | 
0129 | ## 14. Comparações entre arquiteturas, cenários e horizontes
0130 | 
0131 | Produzir painéis comparativos para um mesmo cenário e horizonte, com R0–R3 sobrepostos no espaço F1–F2–F3 e em projeções bidimensionais, mantendo escalas, unidades, limites e cores consistentes. Produzir painéis de evolução E100→E200→E300 no ano de 2026 e comparações E375/2038 e E450/2050 com ressalva explícita de que variam simultaneamente ano e eletrificação. Não inferir efeito temporal isolado quando a frota também muda.
0132 | 
0133 | Para comparar soluções e frentes, registrar quantidade de soluções viáveis/não dominadas, dominância, cobertura entre conjuntos e, se adotados, hipervolume e indicadores IGD/IGD+, sempre com normalização, referência, sentido de otimização e conjunto de referência documentados e constantes nas comparações. Não calcular indicadores tridimensionais com F3 incompleta. Comparações entre R0–R3 exigem fronteiras de custo e ACV equivalentes, inclusive tratamento transparente do CGOB em R3.
0134 | 
0135 | ## 15. Esquema de dados e cadeia de proveniência
0136 | 
0137 | Cada ponto candidato deverá ter candidate_id estável e atributos: run_id, experiment_id, scenario_id, architecture_id, reference_year, temporal_scope_id, economic_horizon_years, seed, generation, candidate_hash, is_feasible, solver_status, mip_gap, max_constraint_residual, F1_brl_per_pkm, F2_kw, F3_kgco2e_per_pkm, F1_status, F2_status, F3_status, is_nondominated_3d, constraint_violation, objective_boundary_version e input_manifest_sha256. Indicadores não disponíveis devem ser NA com motivo explícito, jamais zero substitutivo.
...
0166 |     manifest.json
0167 |     candidates_all.csv
0168 |     candidates_feasible.csv
0169 |     pareto_3d.csv                  # somente se F1/F2/F3 válidos
0170 |     projections/
0171 |     convergence.csv
0172 |     dispatch_timeseries.parquet
0173 |     figures/3d/
...
0185 | 
0186 | Pipeline: (i) validar entradas e status B01–B07; (ii) fixar arquitetura/cenário/horizonte e seed; (iii) executar NSGA-II + MILP com rastreabilidade; (iv) auditar factibilidade e funções objetivo; (v) consolidar candidatos; (vi) calcular não dominância no espaço objetivo válido, com minimização e tolerâncias documentadas; (vii) gerar tabelas e figuras exclusivamente a partir de arquivos auditados; (viii) gerar manifesto e checksums; (ix) reproduzir figuras em ambiente limpo; (x) publicar resultados com suas limitações.
0187 | 
0188 | Testes adicionais: T-P01 unicidade dos identificadores; T-P02 compatibilidade de unidades; T-P03 nenhuma solução inviável na frente; T-P04 algoritmo de não dominância validado por conjunto manual; T-P05 correspondência de cada ponto plotado ao CSV; T-P06 impossibilidade de frente 3D sem F3 completa; T-P07 eixos, escalas e legendas; T-P08 reprodutibilidade por seed/versões; T-P09 comparabilidade entre cenários; T-P10 preservação de todos os candidatos e logs.
0189 | 
0190 | ## 18. Critério de congelamento e uso no artigo
0191 | 
0192 | A inclusão das figuras e da organização de resultados é uma extensão documental de saída, não uma homologação dos experimentos. Congelar o contrato de arquivos e figuras antes de iniciar as execuções definitivas. Na Metodologia, descrever o procedimento de obtenção das frentes e os critérios de não dominância; nos Resultados, apresentar as figuras e comparações com referências às tabelas e manifestos. Em ausência de F3 completa, não anunciar otimização triobjetiva concluída.
0193 | 
0194 | 
0195 | ## 19. Bloqueios, gates e critérios de aceitação
0196 | 
...
0198 | |---|---|---|
0199 | | B01 | Correspondência temporal solar/demanda | Impede inferência cronológica não reconciliada |
0200 | | B02 | Matriz de ônibus, viagens, conexão e SOC | Impede prova de recarga individual |
0201 | | B03 | Tarifa, demanda e faturamento | Impede F1 tarifário definitivo |
0202 | | B04 | Inventário ACV e fatores faltantes | Impede F3 completa e Pareto 3D definitivo |
0203 | | B05 | Domínios CHP, dinâmica biogás e armazenamento | Condiciona R1–R3 completos |
0204 | | B06 | Anualização, PKM e política temporal | Condiciona F1/F3 comparáveis |
0205 | | B07 | Solver, testes e tolerâncias | Condiciona aceite computacional |
0206 | 
0207 | **Gates M0–M7:** M0 especificação e rastreabilidade congeladas; M1 ingestão e hashes; M2 despacho agregado R0; M3 despacho R1–R3; M4 recarga individual após B02; M5 objetivos F1/F2/F3 somente quando admissíveis; M6 integração NSGA-II; M7 publicação científica auditada. A conclusão de um gate não homologa automaticamente gates posteriores.
0208 | 
0209 | **Testes mínimos T-001–T-016:** unicidade dos 137 IDs, coerência dimensional, não duplicação de demanda, balanço nodal, PCC, PV, BESS, CHP, gás, recarga dual, SOC individual, temporalidade, F1, F2, F3 e vínculo equação–parâmetro–constraint–teste. **Testes T-P01–T-P10:** IDs de resultados, unidades, factibilidade, não dominância, correspondência CSV–figura, bloqueio de 3D incompleta, legibilidade, reprodutibilidade, comparabilidade e preservação de candidatos/logs.
0210 | 
0211 | **Critério de aprovação da revisão:** texto integral e referências cruzadas revisados; nenhuma alteração inadvertida dos 137 IDs; dicionário e equações consistentes; política de resultados e figuras versionada; bloqueios identificados; decisão formal de aprovação registrada. **Critério de aprovação de resultados:** execução admissível, indicadores completos para a modalidade declarada, verificações aprovadas e reprodução independente documentada.
0212 | 
0213 | ## 20. Governança, versionamento e publicação
0214 | 
0215 | O repositório GitHub deve manter histórico de commits, tags por gate, arquivo de decisões, manifestos de execução, hashes de entradas, versões de bibliotecas, configuração do solver e scripts que geram tabelas/figuras. Arquivos protegidos e dados pessoais não serão publicados sem autorização. O protocolo, a Base Mestre e o Anexo A não podem ser alterados por um script de experimento. Toda alteração após aprovação requer ID da decisão, motivo, impacto sobre equações/IDs/testes/resultados e autorização explícita.
0216 | 
0217 | O artigo deve separar **Metodologia** (modelo, fronteiras, algoritmos, testes e construção das frentes), **Resultados** (tabelas e gráficos identificados), **Discussão** (trade-offs, limitações e comparabilidade) e **Reprodutibilidade** (versões, hashes, repositório e disponibilidade). Não anunciar fronteiras 3D finais sem F3 completa.
0218 | 
0219 | ## Anexo A — Especificação matemática e dicionário de notações (parte integrante)
0220 | 
0221 | > Texto técnico consolidado da Especificação Matemática REV02, incorporado para autossuficiência. Identificadores históricos EQ mantidos. Eventuais remissões internas a PC-REV07 significam origem da decisão, não vigência concorrente.
0222 | 
0223 | ## A.1. Escopo científico, arquiteturas e regras de precedência
0224 | 
0225 | O problema possui uma camada externa de **dimensionamento multiobjetivo NSGA-II** e um subproblema interno de **despacho MILP de passo 15 min**. As arquiteturas são R0 (rede/PV/BESS), R1 (CHP com GN físico), R2 (CHP com biogás local e biodigestão) e R3 (CHP com GN físico e atributo CGOB separado). A recarga integral dos ônibus é obrigatória; a importação no PCC é limitada a 2.500 kW e a exportação é nula. Os cenários são E100, E200, E300 em 2026, E375 em 2038 e E450 em 2050. Frota total 450 é **hipótese sintética**.
0226 | 
0227 | **Precedência:** (1) decisão vigente do PC-REV07; (2) valor e unidade da Base Mestre congelada; (3) evidência histórica para interpretação, sem sobrescrita; (4) este documento para definição de equações e verificações. Em caso de conflito, bloquear a avaliação correspondente e registrar decisão; não selecionar valores por conveniência.
0228 | 
0229 | **Dois níveis de execução:** - **R0-A, agregado, desenvolvimento:** pode testar balanços, PV/BESS, importação e F2 no horizonte de 70 dias; não demonstra factibilidade individual de recarga, custo anual F1 nem ACV completa F3. - **R0-I/R1-I/R2-I/R3-I, completos:** requerem B01–B06 resolvidos nas partes pertinentes e validação B07. Não converter teste exploratório em resultado científico homologado.
0230 | 
0231 | ## A.2. Notação, conjuntos, índices e unidades
0232 | 
0233 | | Símbolo                 | Definição                                     | Unidade                            |
0234 | |-------------------------|-----------------------------------------------|------------------------------------|
0235 | | `s∈S`                   | Cenário E100/E200/E300/E375/E450              | —                                  |
0236 | | `r∈R`                   | Arquitetura R0/R1/R2/R3                       | —                                  |
0237 | | `h∈H_s`                 | Intervalo cronológico efetivo do cenário      | —                                  |
0238 | | `b∈B_s`                 | Ônibus individual sintético, somente após B02 | —                                  |
0239 | | `g∈G`                   | Gabinete de recarga dual                      | —                                  |
0240 | | `y∈Y`                   | Ano do fluxo econômico; `y=0,...,20`          | ano                                |
...
0243 | | `P`                     | Potência média no intervalo                   | kW (AC ou DC indicado)             |
0244 | | `E`                     | Energia/estoque elétrico                      | kWh                                |
0245 | | `C_PV`                  | Capacidade fotovoltaica DC instalada          | kWp                                |
0246 | | `E_B`, `P_PCS`          | Capacidade nominal BESS e potência PCS        | kWh; kW                            |
0247 | | `P_CHP`                 | Potência nominal elétrica bruta CHP           | kWe                                |
0248 | | `V_BG`, `V_GN`, `V_CH4` | Volume normalizado de biogás, GN e metano     | Nm³                                |
0249 | | `m_sub`                 | Massa úmida de substrato                      | t                                  |
0250 | | `V_D`, `V_G`            | Volume físico digestor e gasômetro            | m³; Nm³ quando estoque padronizado |
...
0271 | 
0272 | | Símbolo                 | Significado                              | Unidade |
0273 | |-------------------------|------------------------------------------|---------|
0274 | | P_grid,h                | importação PCC                           | kW      |
0275 | | P_export,h              | exportação PCC                           | kW      |
0276 | | P_pv,h; P_curt,h        | PV utilizada; corte PV                   | kW      |
0277 | | φ_h                     | produção específica solar                | kW/kWp  |
0278 | | P_PV,ref,h; C_PV,ref    | referência solar; potência da referência | kW; kWp |
0279 | | C_PV,max; n_PV          | teto PV; índice inteiro da malha         | kWp; —  |
0280 | | L_base,h; L_charge,AC,h | carga base; recarga em AC                | kW      |
0281 | | L_aux,h; L_REV09,h      | auxiliares; demanda agregada REV09       | kW      |
0282 | 
0283 | **2 — BESS**
0284 | 
0285 | | Símbolo             | Significado                      | Unidade |
0286 | |---------------------|----------------------------------|---------|
0287 | | E_B,h; E_B,h+1      | energia armazenada no início/fim | kWh     |
...
0331 | | C_substrate,y; C_CGOB,y; C_replacement,y  | substrato, CGOB e reposições                     | BRL2026                  |
0332 | | τ_energy,h; τ_demand,m                    | tarifas de energia e demanda                     | BRL/kWh; BRL/(kW·mês)    |
0333 | | P_peak,m; z_s,r                           | pico mensal; epígrafe de pico                    | kW                       |
0334 | | F1; F2; F3                                | objetivos econômico, pico, ambiental             | BRL/PKM; kW; kgCO₂e/PKM  |
0335 | | GHG_assets; GHG_operation; GHG_EOL        | emissões incorporadas, operacionais, fim de vida | kgCO₂e                   |
0336 | | GHG_grid; GHG_upstream; GHG_fugitive      | emissões da rede, montante e fugitivas           | kgCO₂e                   |
0337 | | m_CH4,escaped                             | massa de metano emitida                          | kg                       |
0338 | | Ex_in; Ex_useful; Ex_destroyed; Ex_losses | parcelas do balanço exergético                   | kWh exergia              |
...
0343 | 
0344 | ## A.3. Vetor de dimensionamento e condição de linearidade
0345 | 
0346 | **EQ-000 — Decisão externa.** `x=(C_PV,E_B,P_PCS,N_g,P_CHP,escolha_CHP,V_G,escala_digestor,r)` contém somente coordenadas cujo domínio e custo estejam documentados. Variáveis inteiras/categóricas devem usar operadores ou codificação mista explícitos. `x` é **fixado antes** de montar cada MILP. Para R0, `P_CHP=V_G=V_D=0`; R1/R3 não produzem biogás local; R2 incorpora digestão e estoque.
0347 | 
0348 | $$\mathbf{x} = \left( C_{PV},E_{B},P_{PCS},N_{g},P_{CHP},V_{G},V_{D},r \right)$$
0349 | 
0350 | **Propriedade matemática:** com `x` fixo, produtos `P_CHP·u_h`, `P_PCS·u_h`, `C_PV·φ_h` são coeficientes constantes multiplicados por variáveis binárias/contínuas, logo lineares. Não implementar simultaneamente `x` variável e `u_h` binária sem linearização exata e limites justificados. **Catálogo e domínio CHP ainda não demonstrados:** não inventar capacidades discretas.
0351 | 
0352 | **Onde:** x: vetor de dimensionamento externo; C_PV: capacidade fotovoltaica (kWp); E_B: capacidade BESS (kWh); P_PCS: potência do conversor (kW); N_g: número de gabinetes (inteiro); P_CHP: potência nominal CHP (kWe); V_G: armazenamento de gás (Nm³ de estoque, distinguindo volume físico); r: arquitetura. Escolha_CHP e escala_digestor são decisões de domínio ainda condicionado.
0353 | 
0354 | ## A.4. Equações de despacho elétrico e PV
0355 | 
0356 | **EQ-001 — Balanço nodal AC sem déficit (kW).**
...
0361 | 
0362 | `L_base` e `L_charge` são mutuamente separados **somente se a origem dos dados comprovar essa decomposição**. No modo agregado, definir `L_REV09,h` conforme a semântica verificada das colunas e usar `L_REV09,h` no lugar de `L_base + L_charge`, **nunca somar a mesma recarga duas vezes**. Não introduzir slack de demanda como solução admissível. Teste: resíduo absoluto ≤ tolerância física documentada em todos os intervalos.
0363 | 
0364 | **Onde:** P_grid,h: importação no PCC (kW); P_pv,h: PV efetivamente utilizada (kW AC); P_chp,net,h: geração CHP líquida (kWe); P_B,dis,h e P_B,ch,h: descarga e carga BESS (kW AC); L_base,h: carga não veicular (kW); L_charge,AC,h: recarga veicular vista em AC (kW); L_aux,h: auxiliares não descontados da geração (kW); h: intervalo de 15 min. L_REV09,h substitui as cargas agregadas somente após verificação de sua semântica.
0365 | 
0366 | **EQ-002 — PCC e ausência de exportação (kW).**
0367 | 
0368 | $$0 \leq P_{h}^{grid} \leq 2500\ kW,\quad\quad P_{h}^{export} = 0$$
0369 | 
0370 | `0 ≤ P_grid,h ≤ 2500`, `P_export,h = 0`. Se houver carga do carregador em DC, converter para AC antes do balanço. A proibição de exportação implica que excedentes PV/CHP precisam ser cortados, armazenados ou ter despacho reduzido dentro dos limites físicos.
0371 | 
0372 | **Onde:** P_grid,h: potência importada (kW); P_export,h: potência exportada (kW); 2500: limite físico do PCC (kW); h: intervalo. A igualdade de exportação nula é uma restrição rígida.
0373 | 
0374 | **EQ-003 — Recurso solar normalizado.** `φ_h = P_PV,ref,h / C_PV,ref`, com unidade `kW/kWp` (numericamente adimensional), **somente após verificar qual potência nominal foi usada na série de referência**. Não reaplicar o fator de geração de aproximadamente 0,80 se já incorporado no CSV. A série horária de 8.760 pontos e a série de 15 min de 6.720 pontos não são intercambiáveis sem procedimento temporal documentado.
0375 | 
0376 | $$\phi_{h} = \frac{P_{h}^{PV,ref}}{C^{PV,ref}}$$
...
0391 | 
0392 | **Onde:** P_curt,h: potência fotovoltaica disponível não aproveitada (kW); h: intervalo. O corte é distinto de perdas elétricas de conversão.
0393 | 
0394 | ## A.5. BESS — estado, operação e envelhecimento
0395 | 
0396 | **EQ-006 — Balanço de energia BESS (kWh).**
0397 | 
0398 | $$E_{h + 1}^{B} = E_{h}^{B} + 0.922P_{h}^{B,ch}\Delta t - \frac{P_{h}^{B,dis}}{0.922}\Delta t$$
0399 | 
0400 | `E_B,h+1 = E_B,h + 0,922 P_B,ch,h Δt − (P_B,dis,h / 0,922) Δt`.
...
0407 | 
0408 | $$0.10E_{B}SOH_{y} \leq E_{h}^{B} \leq 0.90E_{B}SOH_{y}$$
0409 | 
0410 | **Onde:** E_B: capacidade nominal do BESS (kWh); SOH_y: estado de saúde no ano y (fração); E_B,h: estoque de energia (kWh); 0,10 e 0,90: limites fracionários de SOC.
0411 | 
0412 | **EQ-008 — Potência PCS e exclusividade.**
0413 | 
0414 | $$0 \leq P_{h}^{B,ch} \leq P_{PCS}u_{h}^{B},\quad 0 \leq P_{h}^{B,dis} \leq P_{PCS}\left( 1 - u_{h}^{B} \right)$$
0415 | 
0416 | `0 ≤ P_B,ch,h ≤ P_PCS u_B,h`; `0 ≤ P_B,dis,h ≤ P_PCS(1−u_B,h)`; `u_B,h∈{0,1}`; `0 ≤ P_PCS ≤ 0,55 E_B` no caso-base. Não permitir carga e descarga simultâneas. Para `E_B=0`, exigir `P_PCS=0`.
0417 | 
0418 | **Onde:** P_B,ch,h e P_B,dis,h: potências de carga/descarga (kW); P_PCS: potência nominal do conversor (kW); u_B,h: variável binária de modo de carga; E_B: capacidade BESS (kWh); 0,55: limite C-rate em h⁻¹ (P_PCS/E_B).
0419 | 
0420 | **EQ-009 — Contornos cíclicos.** `E_B,1 = 0,50 E_B SOH_y`; `E_B,H+1 = E_B,1` **somente quando o horizonte modelado justificar fechamento cíclico**. Se dias representativos forem ligados cronologicamente, impor `E_B,final(d) = E_B,inicial(d+1)`; não reiniciar SOC em cada dia sintético.
0421 | 
0422 | $$E_{1}^{B} = 0.50E_{B}SOH_{y},\quad\quad E_{H + 1}^{B} = E_{1}^{B}\quad\text{(somente se fechamento ciclico autorizado)}$$
...
0547 | 
0548 | $$PKM_{s,ano} = 23\sum_{d}^{}N_{d}\sum_{b}^{}km_{b,d}$$
0549 | 
0550 | **Regra temporal mandatória:** a série de demanda possui 70 dias sintéticos, enquanto a solar 15 min possui 70 dias datados em 2025; igualdade de índices não comprova igualdade de datas. **B01 permanece aberto**. Os cenários 2038 e 2050 não são automaticamente anos consecutivos de um VPL iniciado em 2026; definir experimento por ano de referência ou cronograma de transição explícito antes de F1/F3 definitivos.
0551 | 
0552 | **Onde:** PKM_s,ano: serviço anual (passageiros·km); N_d: dias anuais do tipo d (dias/ano); km_b,d: distância percorrida (km/dia); b: ônibus efetivamente atendido; 23: ocupação média (passageiros/ônibus).
0553 | 
0554 | ## A.9. Custos, tarifação e F1
0555 | 
0556 | **EQ-036 — CAPEX (BRL2026).** `CAPEX_direct = 4000 C_PV + 1500 E_B + 900 P_PCS + 250000 N_g + c_CHP,r P_CHP + 500 Cap_dig[t/ano] + 1000 q_treat[Nm³/h] + 1500 V_gas_phys[m³]`, **somando apenas termos aplicáveis à arquitetura**. `c_CHP,R2=8000 R$/kWe`; `c_CHP,R1/R3=6000 R$/kWe`. `CAPEX_total = CAPEX_direct(1+0,10)` para engenharia/contingência, observada a fronteira de itens elegíveis. Não aplicar custo de gasômetro em Nm³ sem converter para m³ físico de projeto.
0557 | 
0558 | $$CAPEX_{total} = 1.10\, CAPEX_{direct}$$
0559 | 
0560 | **Onde:** CAPEX_direct e CAPEX_total: investimentos em BRL2026; C_PV (kWp), E_B (kWh), P_PCS (kW), N_g (gabinetes), P_CHP (kWe), Cap_dig (t/ano), q_treat (Nm³/h), V_gas_phys (m³): bases dimensionais dos custos unitários; c_CHP,r: custo CHP da arquitetura r (BRL/kWe); 0,10: engenharia/contingência.
0561 | 
0562 | **EQ-037 — Fluxo de caixa anual (BRL2026/ano).** `CF_y = CAPEX_y + OPEX_fixed,y + OPEX_variable,y + C_energy,y + C_demand,y + C_fuel,y + C_substrate,y + C_CGOB,y + C_replacement,y − residual_y`. Custos específicos: OPEX PV 1,5% CAPEX/ano; BESS 2,5%; CHP 4%; digestão/tratamento 5%; gasômetro 2%; carregadores 2%. GN entregue R\$3/Nm³; substrato R\$50/t e transporte/preparo R\$40/t; prêmio CGOB R\$0,10/Nm³ equivalente. Reposição inversor PV ano 12 a 15% CAPEX PV; bateria ano 12 a 60% CAPEX inicial bateria; reforma CHP ano 10 a 25% CAPEX inicial CHP. Respeitar arquitetura, contagem de reposições e convenção temporal.
0563 | 
0564 | $$CF_{y} = CAPEX_{y} + OPEX_{y} + C_{y}^{energy} + C_{y}^{demand} + C_{y}^{fuel} + C_{y}^{substrate} + C_{y}^{CGOB} + C_{y}^{replacement} - residual_{y}$$
0565 | 
0566 | **Onde:** CF_y: custo líquido no ano y (BRL2026); CAPEX_y: investimentos; OPEX_fixed,y e OPEX_variable,y: operação/manutenção; C_energy,y: energia; C_demand,y: demanda; C_fuel,y: combustível; C_substrate,y: substrato/logística; C_CGOB,y: atributo; C_replacement,y: reposições; residual_y: recuperação de valor. Todas as parcelas em BRL2026.
...
0571 | 
0572 | **Onde:** C_energy,y: despesa anual de energia (BRL2026); P_grid,h: potência comprada (kW); Δt: 0,25 h; τ_energy,h: tarifa de energia (BRL/kWh); h∈y: intervalos representativos anualizados mediante regra validada.
0573 | 
0574 | **EQ-039 — Demanda tarifária.** `C_demand,y = Σ_{m∈y} τ_demand,m × P_peak,m`, com `P_peak,m ≥ P_grid,h` para `h∈m`; `τ_demand=30 BRL/(kW·mês)` como hipótese-base D05-004. Não multiplicar pico único de 70 dias por 12 sem regra temporal/contratual documentada. Tarifa e pico de demanda são distintos do objetivo F2.
0575 | 
0576 | $$C_{y}^{demand} = \sum_{m \in y}^{}\tau_{m}^{demand}P_{m}^{peak},\quad P_{m}^{peak} \geq P_{h}^{grid}\ \forall h \in m$$
0577 | 
0578 | **Onde:** C_demand,y: despesa anual de demanda (BRL2026); m: mês tarifário; τ_demand,m: tarifa (BRL/kW/mês); P_peak,m: maior potência importada no mês (kW); P_grid,h: importação no intervalo (kW).
0579 | 
0580 | **EQ-040 — F1 (BRL/PKM).**
0581 | 
0582 | $$F_{1} = \frac{CF_{0} + \sum_{y = 1}^{20}\frac{CF_{y}}{(1 + 0.12)^{y}}}{\sum_{y = 1}^{20}\frac{PKM_{y}}{(1 + 0.12)^{y}}}$$
0583 | 
0584 | `F1 = [CF_0 + Σ_{y=1}^{20} CF_y/(1+0,12)^y] / [Σ_{y=1}^{20} PKM_y/(1+0,12)^y]`.
0585 | 
0586 | `CF_0` contém investimento inicial quando desembolsado em `t=0`. O numerador é VPL dos custos do sistema energético; o denominador é VPL dos PKM, sem fabricação/operação do ônibus fora da fronteira definida. O denominador deve ser estritamente positivo. Sensibilidades da taxa real: 6% e 18%. `F1` permanece bloqueada para avaliação definitiva enquanto calendário, fluxos e PKM não forem reconciliados.
0587 | 
0588 | **Onde:** F1: custo presente por serviço presente (BRL2026/PKM); CF_0: desembolso inicial (BRL2026); CF_y: custo líquido anual (BRL2026); PKM_y: passageiros·km anuais; y: ano 1 a 20; 0,12: taxa real anual de desconto.
0589 | 
0590 | ## A.10. Pico de importação F2
0591 | 
0592 | **EQ-041 — F2 (kW).** `F2_s,r(x) = min_{despacho factível} z_s,r` quando o MILP for formulado para minimizar pico, sujeito a `z_s,r ≥ P_grid,h` para todo `h∈H_s`. Se o despacho interno otimizar outra função, o valor relatado é `max_h P_grid,h` da solução escolhida, não o mínimo possível de pico. **O critério de desempate/despacho interno precisa ser explicitamente fixado antes do NSGA-II**; não presumir que a mesma solução minimiza custo e pico. Comparar F2 apenas no mesmo cenário e domínio temporal.
0593 | 
0594 | $$F_{2} = \max_{h \in H_{s}}P_{h}^{grid}$$
0595 | 
0596 | **Onde:** F2_s,r(x): objetivo de pico da arquitetura r no cenário s para dimensionamento x (kW); z_s,r: variável epigráfica de pico (kW); P_grid,h: importação no PCC (kW); H_s: conjunto de intervalos avaliados. O mínimo depende da função efetivamente otimizada pelo MILP.
0597 | 
0598 | ## A.11. ACV, fronteiras e F3
0599 | 
0600 | **EQ-042 — Emissões incorporadas (kgCO₂e).** `GHG_assets = 900 C_PV + 135 E_B + 32,47 Cap_dig[t/ano] + 11,6280409 V_gas_phys[m³] + 105 P_CHP + GHG_PCS + GHG_chargers + GHG_PV_inverter + GHG_EOL + GHG_replacements`, com parcelas apenas aplicáveis e unidades funcionais compatíveis. **D11-013=135** é fator condicional; D11-014/018/019 permanecem sem fator; D11-004 legado de reposição BESS não deve substituir automaticamente a emissão real de fabricação do equipamento de reposição.
0601 | 
0602 | $$GHG_{assets} = GHG_{PV} + GHG_{BESS} + GHG_{CHP} + GHG_{dig} + GHG_{gas} + GHG_{PCS} + GHG_{chargers} + GHG_{other}$$
0603 | 
0604 | **Onde:** GHG_assets: emissões incorporadas (kgCO₂e); C_PV (kWp), E_B (kWh), Cap_dig (t/ano), V_gas_phys (m³), P_CHP (kWe): bases dos fatores; GHG_PCS, GHG_chargers, GHG_PV_inverter, GHG_EOL, GHG_replacements: parcelas adicionais em kgCO₂e, sujeitas a fatores válidos.
0605 | 
0606 | **EQ-043 — Emissões operacionais (kgCO₂e).** `GHG_operation = GHG_grid + GHG_GN_upstream+combustion + GHG_substrate_logistics + GHG_other`; para SIN, selecionar **uma** fronteira consistente: D11-002=0,0461 kgCO₂/kWh (operacional legado) **ou** D11-017=0,0996 kgCO₂e/kWh gerado (ACV histórica condicionada), sem soma direta e sem tratar energia gerada no SIN como energia entregue na garagem sem ajuste documentado. D11-015/016 ausentes.
...
0615 | 
0616 | **Onde:** GHG_CH4: impacto do metano emitido (kgCO₂e); m_CH4,escaped: massa fugitiva de CH4 (kg); 27: potencial de aquecimento global do metano biogênico (kgCO₂e/kgCH4); D11-008/009: frações de perda cuja base física deve ser identificada.
0617 | 
0618 | **EQ-045 — F3 (kgCO₂e/PKM).** `F3 = (GHG_assets + GHG_replacements + GHG_operation + GHG_upstream + GHG_fugitive + GHG_EOL − credits_approved) / Σ_y PKM_y`, com mesma fronteira de horizonte e serviço do experimento. Créditos de digestato e tratamento evitado são zero conforme D11-011/012, não licença para ignorar emissões ausentes. **F3 completa não é computável com fatores D11-014/015/016/018/019 ausentes.** Resultados parciais devem ser rotulados e nunca utilizados como F3 definitiva do NSGA-II triobjetivo.
0619 | 
0620 | $$F_{3} = \frac{GHG_{assets} + GHG_{replacements} + GHG_{operation} + GHG_{upstream} + GHG_{fugitive} + GHG_{EOL} - credits_{approved}}{\sum_{y}^{}PKM_{y}}$$
0621 | 
0622 | **Onde:** F3: emissões por serviço (kgCO₂e/PKM); GHG_assets: fabricação/implantação; GHG_replacements: substituições; GHG_operation: operação; GHG_upstream: cadeias a montante; GHG_fugitive: fugitivas; GHG_EOL: fim de vida; credits_approved: créditos aprovados; PKM_y: serviço anual. Exigir fronteiras não sobrepostas entre parcelas.
0623 | 
0624 | ## A.12. Exergia complementar
0625 | 
0626 | **EQ-046 — Balanço exergético, apenas pós-processamento.** `Ex_in = Ex_useful + Ex_destroyed + Ex_losses` \[kWh de exergia\], sob fronteira e ambiente de referência definidos. Não calcular eficiência exergética ou destruição com `PCI` como se fosse exergia química sem convenção/fator documentado. Exergia não é F4.
...
0631 | 
0632 | ## A.13. Função de avaliação do NSGA-II e contrato do MILP
0633 | 
0634 | **ALG-001.** Para cada `(s,r,x)` validado: (i) checar domínios e arquitetura; (ii) fixar `x`; (iii) construir MILP com dados de cenário imutáveis; (iv) resolver com HiGHS; (v) registrar status, gap e tolerâncias; (vi) testar balanços e fronteiras; (vii) rejeitar solução com déficit, violações ou status não aceito; (viii) calcular indicadores disponíveis em módulo independente; (ix) armazenar rastreabilidade de parâmetros, hash, solver e seed. **Não devolver objetivos numéricos falsos para configurações inviáveis.** Para avaliação triobjetiva, exigir F1/F2/F3 completos e comparáveis; até lá, o protótipo pode operar como teste de despacho e, quando justificado, com objetivos parciais claramente separados.
0635 | 
0636 | A escolha da função escalar do MILP interno (custo operacional, pico ou combinação lexicográfica) **não está fechada por estas fontes**. Esta é uma decisão matemática material: não impor uma preferência sem registro. Os hiperparâmetros do NSGA-II (população, gerações e seeds) são parâmetros experimentais ainda a definir, não valores físicos a inventar.
0637 | 
0638 | ## A.14. Condições de contorno, teste de conservação e aceite
...
0643 | | T-002 | `Δt=0,25 h`; unidade consistente em cada equação                          |
0644 | | T-003 | Demanda agregada e individual mutuamente exclusivas                       |
0645 | | T-004 | Resíduo EQ-001 em todos os intervalos dentro da tolerância declarada      |
0646 | | T-005 | PCC ≤ 2500 kW; exportação = 0; déficit = 0                                |
0647 | | T-006 | PV usado + cortado = PV disponível, sem duplicação de fator               |
0648 | | T-007 | BESS conserva energia com 0,922/0,922; limites SOC e exclusividade        |
0649 | | T-008 | CHP desligado = 0; ligado 50–100%; sem 0,96 multiplicativo                |
0650 | | T-009 | R2 conserva Nm³ biogás; metano e combustível não confundidos              |
0651 | | T-010 | Recarga dual soma ≤ 150 kW DC/gabinete, ≤ 2 conectores                    |
0652 | | T-011 | SOC ônibus em saída ≥ 95% e disponibilidade por ônibus, somente após B02  |
0653 | | T-012 | 70 dias não anualizados sem correspondência aprovada                      |
0654 | | T-013 | F1 com VPL BRL/PKM em horizonte e convenção compatíveis                   |
0655 | | T-014 | F2 como máximo do mesmo domínio do experimento                            |
0656 | | T-015 | F3 bloqueada se fator ACV obrigatório estiver ausente                     |
0657 | | T-016 | Cada equação → parâmetro(s) → constraint Pyomo → teste unitário/regressão |
0658 | 
0659 | **Estado de congelamento:** equações EQ-001–010 e EQ-041 são especificações operacionais prontas para codificação do protótipo agregado, condicionadas à interpretação dos CSV e ao fechamento temporal. EQ-011–021, EQ-029–040 e EQ-042–046 definem a matemática e seus limites, **mas não autorizam execução científica completa** enquanto houver entradas e decisões não resolvidas. A lacuna não pode ser ocultada por zero, interpolação arbitrária ou solução inviável penalizada.
0660 | 
...
0673 | | TAB-01 | Matriz de cenários, arquiteturas e horizontes | `config/experiments` e manifestos | Sempre, com status |
0674 | | TAB-02 | Entradas, capacidades e unidades | Base Mestre + `design_variables.csv` | IDs e fontes presentes |
0675 | | TAB-03 | Factibilidade e status do solver | `candidates_all.csv` | Todos os candidatos contabilizados |
0676 | | TAB-04 | Objetivos por solução elegível | `candidates_feasible.csv` | Estados F1/F2/F3 explícitos |
0677 | | TAB-05 | Indicadores de frentes e comparação | `pareto_3d.csv`, `convergence.csv` | Apenas objetivos completos e comparáveis |
0678 | | FIG-P01 | Pareto tridimensional F1/F2/F3 | `pareto_3d.csv` | Três objetivos homologados |
0679 | | FIG-P02–04 | Projeções da frente 3D | `pareto_3d.csv` | Rotular como projeções |
0680 | | FIG-P05 | Evolução por geração | `convergence.csv` | Indicador e referência documentados |
0681 | | FIG-P06 | Dimensionamentos não dominados | `design_variables.csv` | Mesmo conjunto auditado |
0682 | | FIG-P07 | Perfis cronológicos de despacho | `dispatch_timeseries` | Balanços e domínio válidos |
0683 | | FIG-C01 | Sobreposição de R0–R3 por cenário | frentes comparáveis | Fronteiras uniformes |
0684 | | FIG-C02 | Comparação entre cenários | frentes comparáveis | Não atribuir variação só ao ano |
0685 | | MAN-01 | Manifesto de execução e figuras | JSON/CSV + SHA-256 | Reprodutível |
0686 | 
0687 | **Regra final:** a aprovação documental do PC-REV08 não constitui homologação dos parâmetros pendentes nem dos resultados. Toda figura e tabela deve apontar a execução, fonte de dados, filtro e hash que permitam sua regeneração.

## DOCUMENTO: docs/methodology/source_specification/D28_Documento_Final_Consolidado_REV03_PC_REV08.md

...
0008 | 
0009 | **Identificação:** EM-D28-PC-REV08 / REV03, edição de consolidação pré-implementação  
0010 | **Referências internas:** PC-REV07; Base Mestre D28 de 137 IDs; Plano Mestre de Formulação; Auditoria de Consistência Matemática (24 achados).  
0011 | **Estado:** **CONGELÁVEL COMO ESPECIFICAÇÃO DE ARQUITETURA, NOTAÇÃO, EQUAÇÕES DEFINIDAS E REGRAS DE BLOQUEIO. NÃO HOMOLOGADA COMO MODELO COMPLETO EXECUTÁVEL R0–R3.**  
0012 | **Controle:** nenhuma alteração de hipótese ou parâmetro é autorizada por este documento. Campos `PENDENTE` são contratos explícitos, não valores zero.
0013 | 
0014 | ## 1. Escopo científico, arquiteturas e regras de precedência
0015 | 
0016 | O problema possui uma camada externa de **dimensionamento multiobjetivo NSGA-II** e um subproblema interno de **despacho MILP de passo 15 min**. As arquiteturas são R0 (rede/PV/BESS), R1 (CHP com GN físico), R2 (CHP com biogás local e biodigestão) e R3 (CHP com GN físico e atributo CGOB separado). A recarga integral dos ônibus é obrigatória; a importação no PCC é limitada a 2.500 kW e a exportação é nula. Os cenários são E100, E200, E300 em 2026, E375 em 2038 e E450 em 2050. Frota total 450 é **hipótese sintética**.
0017 | 
0018 | **Precedência proposta, condicionada à aprovação:** (1) decisão vigente do PC-REV08; (2) valor e unidade da Base Mestre congelada; (3) evidência histórica para interpretação, sem sobrescrita; (4) este documento para definição de equações e verificações. Em caso de conflito, bloquear a avaliação correspondente e registrar decisão; não selecionar valores por conveniência.
0019 | 
0020 | **Dois níveis de execução:** - **R0-A, agregado, desenvolvimento:** pode testar balanços, PV/BESS, importação e F2 no horizonte de 70 dias; não demonstra factibilidade individual de recarga, custo anual F1 nem ACV completa F3. - **R0-I/R1-I/R2-I/R3-I, completos:** requerem B01–B06 resolvidos nas partes pertinentes e validação B07. Não converter teste exploratório em resultado científico homologado.
0021 | 
0022 | ## 2. Notação, conjuntos, índices e unidades
0023 | 
0024 | | Símbolo                 | Definição                                     | Unidade                            |
0025 | |-------------------------|-----------------------------------------------|------------------------------------|
0026 | | `s∈S`                   | Cenário E100/E200/E300/E375/E450              | —                                  |
0027 | | `r∈R`                   | Arquitetura R0/R1/R2/R3                       | —                                  |
0028 | | `h∈H_s`                 | Intervalo cronológico efetivo do cenário      | —                                  |
0029 | | `b∈B_s`                 | Ônibus individual sintético, somente após B02 | —                                  |
0030 | | `g∈G`                   | Gabinete de recarga dual                      | —                                  |
0031 | | `y∈Y`                   | Ano do fluxo econômico; `y=0,...,20`          | ano                                |
...
0034 | | `P`                     | Potência média no intervalo                   | kW (AC ou DC indicado)             |
0035 | | `E`                     | Energia/estoque elétrico                      | kWh                                |
0036 | | `C_PV`                  | Capacidade fotovoltaica DC instalada          | kWp                                |
0037 | | `E_B`, `P_PCS`          | Capacidade nominal BESS e potência PCS        | kWh; kW                            |
0038 | | `P_CHP`                 | Potência nominal elétrica bruta CHP           | kWe                                |
0039 | | `V_BG`, `V_GN`, `V_CH4` | Volume normalizado de biogás, GN e metano     | Nm³                                |
0040 | | `m_sub`                 | Massa úmida de substrato                      | t                                  |
0041 | | `V_D`, `V_G`            | Volume físico digestor e gasômetro            | m³; Nm³ quando estoque padronizado |
...
0062 | 
0063 | | Símbolo                 | Significado                              | Unidade |
0064 | |-------------------------|------------------------------------------|---------|
0065 | | P_grid,h                | importação PCC                           | kW      |
0066 | | P_export,h              | exportação PCC                           | kW      |
0067 | | P_pv,h; P_curt,h        | PV utilizada; corte PV                   | kW      |
0068 | | φ_h                     | produção específica solar                | kW/kWp  |
0069 | | P_PV,ref,h; C_PV,ref    | referência solar; potência da referência | kW; kWp |
0070 | | C_PV,max; n_PV          | teto PV; índice inteiro da malha         | kWp; —  |
0071 | | L_base,h; L_charge,AC,h | carga base; recarga em AC                | kW      |
0072 | | L_aux,h; L_REV09,h      | auxiliares; demanda agregada REV09       | kW      |
0073 | 
0074 | **2 — BESS**
0075 | 
0076 | | Símbolo             | Significado                      | Unidade |
0077 | |---------------------|----------------------------------|---------|
0078 | | E_B,h; E_B,h+1      | energia armazenada no início/fim | kWh     |
...
0122 | | C_substrate,y; C_CGOB,y; C_replacement,y  | substrato, CGOB e reposições                     | BRL2026                  |
0123 | | τ_energy,h; τ_demand,m                    | tarifas de energia e demanda                     | BRL/kWh; BRL/(kW·mês)    |
0124 | | P_peak,m; z_s,r                           | pico mensal; epígrafe de pico                    | kW                       |
0125 | | F1; F2; F3                                | objetivos econômico, pico, ambiental             | BRL/PKM; kW; kgCO₂e/PKM  |
0126 | | GHG_assets; GHG_operation; GHG_EOL        | emissões incorporadas, operacionais, fim de vida | kgCO₂e                   |
0127 | | GHG_grid; GHG_upstream; GHG_fugitive      | emissões da rede, montante e fugitivas           | kgCO₂e                   |
0128 | | m_CH4,escaped                             | massa de metano emitida                          | kg                       |
0129 | | Ex_in; Ex_useful; Ex_destroyed; Ex_losses | parcelas do balanço exergético                   | kWh exergia              |
...
0134 | 
0135 | ## 3. Vetor de dimensionamento e condição de linearidade
0136 | 
0137 | **EQ-000 — Decisão externa.** `x=(C_PV,E_B,P_PCS,N_g,P_CHP,escolha_CHP,V_G,escala_digestor,r)` contém somente coordenadas cujo domínio e custo estejam documentados. Variáveis inteiras/categóricas devem usar operadores ou codificação mista explícitos. `x` é **fixado antes** de montar cada MILP. Para R0, `P_CHP=V_G=V_D=0`; R1/R3 não produzem biogás local; R2 incorpora digestão e estoque.
0138 | 
0139 | $$\mathbf{x} = \left( C_{PV},E_{B},P_{PCS},N_{g},P_{CHP},V_{G},V_{D},r \right)$$
0140 | 
0141 | **Propriedade matemática:** com `x` fixo, produtos `P_CHP·u_h`, `P_PCS·u_h`, `C_PV·φ_h` são coeficientes constantes multiplicados por variáveis binárias/contínuas, logo lineares. Não implementar simultaneamente `x` variável e `u_h` binária sem linearização exata e limites justificados. **Catálogo e domínio CHP ainda não demonstrados:** não inventar capacidades discretas.
0142 | 
0143 | **Onde:** x: vetor de dimensionamento externo; C_PV: capacidade fotovoltaica (kWp); E_B: capacidade BESS (kWh); P_PCS: potência do conversor (kW); N_g: número de gabinetes (inteiro); P_CHP: potência nominal CHP (kWe); V_G: armazenamento de gás (Nm³ de estoque, distinguindo volume físico); r: arquitetura. Escolha_CHP e escala_digestor são decisões de domínio ainda condicionado.
0144 | 
0145 | ## 4. Equações de despacho elétrico e PV
0146 | 
0147 | **EQ-001 — Balanço nodal AC sem déficit (kW).**
...
0152 | 
0153 | `L_base` e `L_charge` são mutuamente separados **somente se a origem dos dados comprovar essa decomposição**. No modo agregado, definir `L_REV09,h` conforme a semântica verificada das colunas e usar `L_REV09,h` no lugar de `L_base + L_charge`, **nunca somar a mesma recarga duas vezes**. Não introduzir slack de demanda como solução admissível. Teste: resíduo absoluto ≤ tolerância física documentada em todos os intervalos.
0154 | 
0155 | **Onde:** P_grid,h: importação no PCC (kW); P_pv,h: PV efetivamente utilizada (kW AC); P_chp,net,h: geração CHP líquida (kWe); P_B,dis,h e P_B,ch,h: descarga e carga BESS (kW AC); L_base,h: carga não veicular (kW); L_charge,AC,h: recarga veicular vista em AC (kW); L_aux,h: auxiliares não descontados da geração (kW); h: intervalo de 15 min. L_REV09,h substitui as cargas agregadas somente após verificação de sua semântica.
0156 | 
0157 | **EQ-002 — PCC e ausência de exportação (kW).**
0158 | 
0159 | $$0 \leq P_{h}^{grid} \leq 2500\ kW,\quad\quad P_{h}^{export} = 0$$
0160 | 
0161 | `0 ≤ P_grid,h ≤ 2500`, `P_export,h = 0`. Se houver carga do carregador em DC, converter para AC antes do balanço. A proibição de exportação implica que excedentes PV/CHP precisam ser cortados, armazenados ou ter despacho reduzido dentro dos limites físicos.
0162 | 
0163 | **Onde:** P_grid,h: potência importada (kW); P_export,h: potência exportada (kW); 2500: limite físico do PCC (kW); h: intervalo. A igualdade de exportação nula é uma restrição rígida.
0164 | 
0165 | **EQ-003 — Recurso solar normalizado.** `φ_h = P_PV,ref,h / C_PV,ref`, com unidade `kW/kWp` (numericamente adimensional), **somente após verificar qual potência nominal foi usada na série de referência**. Não reaplicar o fator de geração de aproximadamente 0,80 se já incorporado no CSV. A série horária de 8.760 pontos e a série de 15 min de 6.720 pontos não são intercambiáveis sem procedimento temporal documentado.
0166 | 
0167 | $$\phi_{h} = \frac{P_{h}^{PV,ref}}{C^{PV,ref}}$$
...
0182 | 
0183 | **Onde:** P_curt,h: potência fotovoltaica disponível não aproveitada (kW); h: intervalo. O corte é distinto de perdas elétricas de conversão.
0184 | 
0185 | ## 5. BESS — estado, operação e envelhecimento
0186 | 
0187 | **EQ-006 — Balanço de energia BESS (kWh).**
0188 | 
0189 | $$E_{h + 1}^{B} = E_{h}^{B} + 0.922P_{h}^{B,ch}\Delta t - \frac{P_{h}^{B,dis}}{0.922}\Delta t$$
0190 | 
0191 | `E_B,h+1 = E_B,h + 0,922 P_B,ch,h Δt − (P_B,dis,h / 0,922) Δt`.
...
0198 | 
0199 | $$0.10E_{B}SOH_{y} \leq E_{h}^{B} \leq 0.90E_{B}SOH_{y}$$
0200 | 
0201 | **Onde:** E_B: capacidade nominal do BESS (kWh); SOH_y: estado de saúde no ano y (fração); E_B,h: estoque de energia (kWh); 0,10 e 0,90: limites fracionários de SOC.
0202 | 
0203 | **EQ-008 — Potência PCS e exclusividade.**
0204 | 
0205 | $$0 \leq P_{h}^{B,ch} \leq P_{PCS}u_{h}^{B},\quad 0 \leq P_{h}^{B,dis} \leq P_{PCS}\left( 1 - u_{h}^{B} \right)$$
0206 | 
0207 | `0 ≤ P_B,ch,h ≤ P_PCS u_B,h`; `0 ≤ P_B,dis,h ≤ P_PCS(1−u_B,h)`; `u_B,h∈{0,1}`; `0 ≤ P_PCS ≤ 0,55 E_B` no caso-base. Não permitir carga e descarga simultâneas. Para `E_B=0`, exigir `P_PCS=0`.
0208 | 
0209 | **Onde:** P_B,ch,h e P_B,dis,h: potências de carga/descarga (kW); P_PCS: potência nominal do conversor (kW); u_B,h: variável binária de modo de carga; E_B: capacidade BESS (kWh); 0,55: limite C-rate em h⁻¹ (P_PCS/E_B).
0210 | 
0211 | **EQ-009 — Contornos cíclicos.** `E_B,1 = 0,50 E_B SOH_y`; `E_B,H+1 = E_B,1` **somente quando o horizonte modelado justificar fechamento cíclico**. Se dias representativos forem ligados cronologicamente, impor `E_B,final(d) = E_B,inicial(d+1)`; não reiniciar SOC em cada dia sintético.
0212 | 
0213 | $$E_{1}^{B} = 0.50E_{B}SOH_{y},\quad\quad E_{H + 1}^{B} = E_{1}^{B}\quad\text{(somente se fechamento ciclico autorizado)}$$
...
0338 | 
0339 | $$PKM_{s,ano} = 23\sum_{d}^{}N_{d}\sum_{b}^{}km_{b,d}$$
0340 | 
0341 | **Regra temporal mandatória:** a série de demanda possui 70 dias sintéticos, enquanto a solar 15 min possui 70 dias datados em 2025; igualdade de índices não comprova igualdade de datas. **B01 permanece aberto**. Os cenários 2038 e 2050 não são automaticamente anos consecutivos de um VPL iniciado em 2026; definir experimento por ano de referência ou cronograma de transição explícito antes de F1/F3 definitivos.
0342 | 
0343 | **Onde:** PKM_s,ano: serviço anual (passageiros·km); N_d: dias anuais do tipo d (dias/ano); km_b,d: distância percorrida (km/dia); b: ônibus efetivamente atendido; 23: ocupação média (passageiros/ônibus).
0344 | 
0345 | ## 9. Custos, tarifação e F1
0346 | 
0347 | **EQ-036 — CAPEX (BRL2026).** `CAPEX_direct = 4000 C_PV + 1500 E_B + 900 P_PCS + 250000 N_g + c_CHP,r P_CHP + 500 Cap_dig[t/ano] + 1000 q_treat[Nm³/h] + 1500 V_gas_phys[m³]`, **somando apenas termos aplicáveis à arquitetura**. `c_CHP,R2=8000 R$/kWe`; `c_CHP,R1/R3=6000 R$/kWe`. `CAPEX_total = CAPEX_direct(1+0,10)` para engenharia/contingência, observada a fronteira de itens elegíveis. Não aplicar custo de gasômetro em Nm³ sem converter para m³ físico de projeto.
0348 | 
0349 | $$CAPEX_{total} = 1.10\, CAPEX_{direct}$$
0350 | 
0351 | **Onde:** CAPEX_direct e CAPEX_total: investimentos em BRL2026; C_PV (kWp), E_B (kWh), P_PCS (kW), N_g (gabinetes), P_CHP (kWe), Cap_dig (t/ano), q_treat (Nm³/h), V_gas_phys (m³): bases dimensionais dos custos unitários; c_CHP,r: custo CHP da arquitetura r (BRL/kWe); 0,10: engenharia/contingência.
0352 | 
0353 | **EQ-037 — Fluxo de caixa anual (BRL2026/ano).** `CF_y = CAPEX_y + OPEX_fixed,y + OPEX_variable,y + C_energy,y + C_demand,y + C_fuel,y + C_substrate,y + C_CGOB,y + C_replacement,y − residual_y`. Custos específicos: OPEX PV 1,5% CAPEX/ano; BESS 2,5%; CHP 4%; digestão/tratamento 5%; gasômetro 2%; carregadores 2%. GN entregue R\$3/Nm³; substrato R\$50/t e transporte/preparo R\$40/t; prêmio CGOB R\$0,10/Nm³ equivalente. Reposição inversor PV ano 12 a 15% CAPEX PV; bateria ano 12 a 60% CAPEX inicial bateria; reforma CHP ano 10 a 25% CAPEX inicial CHP. Respeitar arquitetura, contagem de reposições e convenção temporal.
0354 | 
0355 | $$CF_{y} = CAPEX_{y} + OPEX_{y} + C_{y}^{energy} + C_{y}^{demand} + C_{y}^{fuel} + C_{y}^{substrate} + C_{y}^{CGOB} + C_{y}^{replacement} - residual_{y}$$
0356 | 
0357 | **Onde:** CF_y: custo líquido no ano y (BRL2026); CAPEX_y: investimentos; OPEX_fixed,y e OPEX_variable,y: operação/manutenção; C_energy,y: energia; C_demand,y: demanda; C_fuel,y: combustível; C_substrate,y: substrato/logística; C_CGOB,y: atributo; C_replacement,y: reposições; residual_y: recuperação de valor. Todas as parcelas em BRL2026.
...
0362 | 
0363 | **Onde:** C_energy,y: despesa anual de energia (BRL2026); P_grid,h: potência comprada (kW); Δt: 0,25 h; τ_energy,h: tarifa de energia (BRL/kWh); h∈y: intervalos representativos anualizados mediante regra validada.
0364 | 
0365 | **EQ-039 — Demanda tarifária.** `C_demand,y = Σ_{m∈y} τ_demand,m × P_peak,m`, com `P_peak,m ≥ P_grid,h` para `h∈m`; `τ_demand=30 BRL/(kW·mês)` como hipótese-base D05-004. Não multiplicar pico único de 70 dias por 12 sem regra temporal/contratual documentada. Tarifa e pico de demanda são distintos do objetivo F2.
0366 | 
0367 | $$C_{y}^{demand} = \sum_{m \in y}^{}\tau_{m}^{demand}P_{m}^{peak},\quad P_{m}^{peak} \geq P_{h}^{grid}\ \forall h \in m$$
0368 | 
0369 | **Onde:** C_demand,y: despesa anual de demanda (BRL2026); m: mês tarifário; τ_demand,m: tarifa (BRL/kW/mês); P_peak,m: maior potência importada no mês (kW); P_grid,h: importação no intervalo (kW).
0370 | 
0371 | **EQ-040 — F1 (BRL/PKM).**
0372 | 
0373 | $$F_{1} = \frac{CF_{0} + \sum_{y = 1}^{20}\frac{CF_{y}}{(1 + 0.12)^{y}}}{\sum_{y = 1}^{20}\frac{PKM_{y}}{(1 + 0.12)^{y}}}$$
0374 | 
0375 | `F1 = [CF_0 + Σ_{y=1}^{20} CF_y/(1+0,12)^y] / [Σ_{y=1}^{20} PKM_y/(1+0,12)^y]`.
0376 | 
0377 | `CF_0` contém investimento inicial quando desembolsado em `t=0`. O numerador é VPL dos custos do sistema energético; o denominador é VPL dos PKM, sem fabricação/operação do ônibus fora da fronteira definida. O denominador deve ser estritamente positivo. Sensibilidades da taxa real: 6% e 18%. `F1` permanece bloqueada para avaliação definitiva enquanto calendário, fluxos e PKM não forem reconciliados.
0378 | 
0379 | **Onde:** F1: custo presente por serviço presente (BRL2026/PKM); CF_0: desembolso inicial (BRL2026); CF_y: custo líquido anual (BRL2026); PKM_y: passageiros·km anuais; y: ano 1 a 20; 0,12: taxa real anual de desconto.
0380 | 
0381 | ## 10. Pico de importação F2
0382 | 
0383 | **EQ-041 — F2 (kW).** `F2_s,r(x) = min_{despacho factível} z_s,r` quando o MILP for formulado para minimizar pico, sujeito a `z_s,r ≥ P_grid,h` para todo `h∈H_s`. Se o despacho interno otimizar outra função, o valor relatado é `max_h P_grid,h` da solução escolhida, não o mínimo possível de pico. **O critério de desempate/despacho interno precisa ser explicitamente fixado antes do NSGA-II**; não presumir que a mesma solução minimiza custo e pico. Comparar F2 apenas no mesmo cenário e domínio temporal.
0384 | 
0385 | $$F_{2} = \max_{h \in H_{s}}P_{h}^{grid}$$
0386 | 
0387 | **Onde:** F2_s,r(x): objetivo de pico da arquitetura r no cenário s para dimensionamento x (kW); z_s,r: variável epigráfica de pico (kW); P_grid,h: importação no PCC (kW); H_s: conjunto de intervalos avaliados. O mínimo depende da função efetivamente otimizada pelo MILP.
0388 | 
0389 | ## 11. ACV, fronteiras e F3
0390 | 
0391 | **EQ-042 — Emissões incorporadas (kgCO₂e).** `GHG_assets = 900 C_PV + 135 E_B + 32,47 Cap_dig[t/ano] + 11,6280409 V_gas_phys[m³] + 105 P_CHP + GHG_PCS + GHG_chargers + GHG_PV_inverter + GHG_EOL + GHG_replacements`, com parcelas apenas aplicáveis e unidades funcionais compatíveis. **D11-013=135** é fator condicional; D11-014/018/019 permanecem sem fator; D11-004 legado de reposição BESS não deve substituir automaticamente a emissão real de fabricação do equipamento de reposição.
0392 | 
0393 | $$GHG_{assets} = GHG_{PV} + GHG_{BESS} + GHG_{CHP} + GHG_{dig} + GHG_{gas} + GHG_{PCS} + GHG_{chargers} + GHG_{other}$$
0394 | 
0395 | **Onde:** GHG_assets: emissões incorporadas (kgCO₂e); C_PV (kWp), E_B (kWh), Cap_dig (t/ano), V_gas_phys (m³), P_CHP (kWe): bases dos fatores; GHG_PCS, GHG_chargers, GHG_PV_inverter, GHG_EOL, GHG_replacements: parcelas adicionais em kgCO₂e, sujeitas a fatores válidos.
0396 | 
0397 | **EQ-043 — Emissões operacionais (kgCO₂e).** `GHG_operation = GHG_grid + GHG_GN_upstream+combustion + GHG_substrate_logistics + GHG_other`; para SIN, selecionar **uma** fronteira consistente: D11-002=0,0461 kgCO₂/kWh (operacional legado) **ou** D11-017=0,0996 kgCO₂e/kWh gerado (ACV histórica condicionada), sem soma direta e sem tratar energia gerada no SIN como energia entregue na garagem sem ajuste documentado. D11-015/016 ausentes.
...
0406 | 
0407 | **Onde:** GHG_CH4: impacto do metano emitido (kgCO₂e); m_CH4,escaped: massa fugitiva de CH4 (kg); 27: potencial de aquecimento global do metano biogênico (kgCO₂e/kgCH4); D11-008/009: frações de perda cuja base física deve ser identificada.
0408 | 
0409 | **EQ-045 — F3 (kgCO₂e/PKM).** `F3 = (GHG_assets + GHG_replacements + GHG_operation + GHG_upstream + GHG_fugitive + GHG_EOL − credits_approved) / Σ_y PKM_y`, com mesma fronteira de horizonte e serviço do experimento. Créditos de digestato e tratamento evitado são zero conforme D11-011/012, não licença para ignorar emissões ausentes. **F3 completa não é computável com fatores D11-014/015/016/018/019 ausentes.** Resultados parciais devem ser rotulados e nunca utilizados como F3 definitiva do NSGA-II triobjetivo.
0410 | 
0411 | $$F_{3} = \frac{GHG_{assets} + GHG_{replacements} + GHG_{operation} + GHG_{upstream} + GHG_{fugitive} + GHG_{EOL} - credits_{approved}}{\sum_{y}^{}PKM_{y}}$$
0412 | 
0413 | **Onde:** F3: emissões por serviço (kgCO₂e/PKM); GHG_assets: fabricação/implantação; GHG_replacements: substituições; GHG_operation: operação; GHG_upstream: cadeias a montante; GHG_fugitive: fugitivas; GHG_EOL: fim de vida; credits_approved: créditos aprovados; PKM_y: serviço anual. Exigir fronteiras não sobrepostas entre parcelas.
0414 | 
0415 | ## 12. Exergia complementar
0416 | 
0417 | **EQ-046 — Balanço exergético, apenas pós-processamento.** `Ex_in = Ex_useful + Ex_destroyed + Ex_losses` \[kWh de exergia\], sob fronteira e ambiente de referência definidos. Não calcular eficiência exergética ou destruição com `PCI` como se fosse exergia química sem convenção/fator documentado. Exergia não é F4.
...
0422 | 
0423 | ## 13. Função de avaliação do NSGA-II e contrato do MILP
0424 | 
0425 | **ALG-001.** Para cada `(s,r,x)` validado: (i) checar domínios e arquitetura; (ii) fixar `x`; (iii) construir MILP com dados de cenário imutáveis; (iv) resolver com HiGHS; (v) registrar status, gap e tolerâncias; (vi) testar balanços e fronteiras; (vii) rejeitar solução com déficit, violações ou status não aceito; (viii) calcular indicadores disponíveis em módulo independente; (ix) armazenar rastreabilidade de parâmetros, hash, solver e seed. **Não devolver objetivos numéricos falsos para configurações inviáveis.** Para avaliação triobjetiva, exigir F1/F2/F3 completos e comparáveis; até lá, o protótipo pode operar como teste de despacho e, quando justificado, com objetivos parciais claramente separados.
0426 | 
0427 | A escolha da função escalar do MILP interno (custo operacional, pico ou combinação lexicográfica) **não está fechada por estas fontes**. Esta é uma decisão matemática material: não impor uma preferência sem registro. Os hiperparâmetros do NSGA-II (população, gerações e seeds) são parâmetros experimentais ainda a definir, não valores físicos a inventar.
0428 | 
0429 | ## 14. Condições de contorno, teste de conservação e aceite
...
0434 | | T-002 | `Δt=0,25 h`; unidade consistente em cada equação                          |
0435 | | T-003 | Demanda agregada e individual mutuamente exclusivas                       |
0436 | | T-004 | Resíduo EQ-001 em todos os intervalos dentro da tolerância declarada      |
0437 | | T-005 | PCC ≤ 2500 kW; exportação = 0; déficit = 0                                |
0438 | | T-006 | PV usado + cortado = PV disponível, sem duplicação de fator               |
0439 | | T-007 | BESS conserva energia com 0,922/0,922; limites SOC e exclusividade        |
0440 | | T-008 | CHP desligado = 0; ligado 50–100%; sem 0,96 multiplicativo                |
0441 | | T-009 | R2 conserva Nm³ biogás; metano e combustível não confundidos              |
0442 | | T-010 | Recarga dual soma ≤ 150 kW DC/gabinete, ≤ 2 conectores                    |
0443 | | T-011 | SOC ônibus em saída ≥ 95% e disponibilidade por ônibus, somente após B02  |
0444 | | T-012 | 70 dias não anualizados sem correspondência aprovada                      |
0445 | | T-013 | F1 com VPL BRL/PKM em horizonte e convenção compatíveis                   |
0446 | | T-014 | F2 como máximo do mesmo domínio do experimento                            |
0447 | | T-015 | F3 bloqueada se fator ACV obrigatório estiver ausente                     |
0448 | | T-016 | Cada equação → parâmetro(s) → constraint Pyomo → teste unitário/regressão |
0449 | 
0450 | **Estado de congelamento:** equações EQ-001–010 e EQ-041 são especificações operacionais prontas para codificação do protótipo agregado, condicionadas à interpretação dos CSV e ao fechamento temporal. EQ-011–021, EQ-029–040 e EQ-042–046 definem a matemática e seus limites, **mas não autorizam execução científica completa** enquanto houver entradas e decisões não resolvidas. A lacuna não pode ser ocultada por zero, interpolação arbitrária ou solução inviável penalizada.
0451 | 
...
0457 | 
0458 | ## 16. Redação científica — estrutura sugerida da Metodologia
0459 | 
0460 | 1.  **Objeto e cenários:** garagem D28, frota sintética, E100–E450, arquiteturas R0–R3 e fronteiras.
0461 | 2.  **Dados:** INMET A701/A771, séries solares, demanda REV09, calendário de 70 dias e limitações de pareamento.
0462 | 3.  **Dimensionamento:** vetor externo NSGA-II, domínios, variáveis discretas e limites geométricos.
0463 | 4.  **Despacho:** MILP de 15 minutos, balanço AC, PCC, PV, BESS, CHP, biodigestão e recarga dual.
0464 | 5.  **Objetivos:** VPL custos/VPL PKM (F1), pico importado (F2), ACV energética/PKM (F3); exergia complementar.
0465 | 6.  **Implementação:** Python, Pyomo, HiGHS, pymoo, controle Git/GitHub e hash das entradas.
0466 | 7.  **Validação e limitações:** factibilidade física, testes de conservação, sensibilidade, disponibilidade e pendências de ACV/recarga individual.
0467 | 
0468 | **Importante:** esta seção é roteiro metodológico; não afirmar que experimentos, sensibilidade, convergência ou validação já foram executados.
...
0470 | 
0471 | ## 18. Controle de revisão REV03 e correspondência com PC-REV08
0472 | 
0473 | **Situação documental:** especificação técnica REV03, subordinada ao PC-REV08 **proposto**, cuja vigência normativa depende de aprovação formal. A Base Mestre PC-REV07 com 137 IDs continua congelada; esta revisão não altera parâmetros, unidades, equações EQ-000–EQ-046 nem homologa bloqueios pendentes. Preservam-se os significados de F1 (BRL/PKM), F2 (kW) e F3 (kgCO₂e/PKM). A revisão consiste na inclusão de um contrato verificável de resultados, figuras, tabelas e proveniência.
0474 | 
0475 | ### 18.1. Identificadores e granularidade
0476 | 
0477 | Cada execução terá `experiment_id`, `architecture_id` (R0–R3), `scenario_id` (E100/E200/E300/E375/E450), `reference_year` (2026/2038/2050), `run_id`, `seed`, `input_manifest_sha256`, `config_sha256`, `git_commit`, versões do solver e da plataforma, data UTC e estado de validação. Não confundir ano de referência com os 70 dias sintéticos de despacho, seus 6720 intervalos de 15 minutos ou o horizonte econômico de 20 anos. O desenho contempla até 20 células arquitetura × cenário; executar apenas as admissíveis e registrar as exclusões.
0478 | 
0479 | ### 18.2. Definição operacional da fronteira triobjetiva
0480 | 
0481 | A solução candidata é elegível somente se todos os requisitos físicos, temporais, de atendimento da frota e do solver estiverem satisfeitos e os três objetivos forem finitos, rastreáveis e calculados com os mesmos limites de sistema. Para duas soluções elegíveis `a` e `b`, `a` domina `b` se `F_i(a) <= F_i(b)` para todo `i` em {1,2,3} e houver ao menos um objetivo estritamente menor. A fronteira `pareto_3d.csv` reúne as soluções elegíveis não dominadas, segundo tolerâncias numéricas documentadas, sem agregação de objetivos nem descarte arbitrário de extremos. Empates e duplicatas exigem regra determinística registrada.
0482 | 
0483 | As projeções F1×F2, F1×F3 e F2×F3 são **projeções da fronteira triobjetiva** e não devem ser rotuladas como frentes recalculadas de dois objetivos. Comparações entre arquiteturas podem representar sobreposição de frentes, mas não autorizam comparar pontos de diferentes anos, perfis de demanda ou denominadores PKM sem explicitar a base comum e as ressalvas.
0484 | 
0485 | ### 18.3. Contrato de tabelas e arquivos
0486 | 
0487 | | Artefato | Conteúdo mínimo | Condição de uso |
0488 | |---|---|---|
0489 | | `candidates_all.csv` | IDs, vetor de decisão, status, objetivos ou motivo de ausência, seed, geração | Todos os candidatos avaliados |
0490 | | `candidates_feasible.csv` | Soluções factíveis, três objetivos, métricas e vínculo com despacho | Após checagem de factibilidade |
0491 | | `pareto_3d.csv` | Soluções não dominadas e objetivos F1/F2/F3, unidades e IDs | Somente com F3 validado |
0492 | | `convergence.csv` | Geração, avaliações, contagem factível, indicadores e parâmetros do indicador | Não declarar convergência por inspeção visual isolada |
0493 | | `dispatch_timeseries.parquet` | Série temporal, solução, dia, passo, potências, SOC, importação e estados pertinentes | Checagem energética e reprodução |
0494 | | `figures_manifest.csv` | ID da figura, tipo, fonte, hash, filtros, código, versão, status | Obrigatório para cada figura |
0495 | | `manifest.json` | Configuração, fontes, hashes, software, seed, bloqueios, validação e escopo | Obrigatório por execução |
0496 | 
0497 | Tabelas científicas mínimas: matriz de experimentos e admissibilidade; parâmetros e premissas com proveniência; desempenho da otimização e factibilidade; métricas das soluções representativas; comparações R0–R3 por cenário/ano; sensibilidade e limitações, quando aplicáveis. Resultados monetários primários em BRL e conversões internacionais com câmbio, data e método documentados.
0498 | 
0499 | ### 18.4. Contrato de figuras
0500 | 
0501 | Por célula admissível, produzir, quando os dados forem elegíveis: (i) Pareto F1–F2–F3 tridimensional; (ii) projeções F1×F2, F1×F3 e F2×F3; (iii) convergência/qualidade e diversidade, com definição do indicador; (iv) dispersão dos dimensionamentos; (v) perfis de despacho para soluções representativas e extremos de cada objetivo. Para comparações, padronizar escalas e unidades e distinguir arquiteturas, cenários e anos. Toda legenda deve identificar estado do resultado, critérios de seleção e execução de origem. Publicar figuras em formato vetorial (`.svg` ou `.pdf`) e, quando necessário, `.png` de alta resolução, mantendo código e dados de origem.
0502 | 
0503 | ### 18.5. Bloqueio de publicação triobjetiva
0504 | 
0505 | Enquanto fatores de ACV necessários, inclusive D11-014, D11-015, D11-016, D11-018 e D11-019, ou quaisquer outros requisitos de F3 estiverem abertos, **não** gerar ou identificar `pareto_3d.csv` e figuras F1–F2–F3 como definitivos. É permitido diagnóstico exploratório claramente identificado, sem imputação zero para ausências e sem equipará-lo a resultado científico validado. A factibilidade por ônibus depende do fechamento de B02; a representação agregada não a substitui.
0506 | 
0507 | ### 18.6. Estrutura vinculante do repositório
0508 | 
0509 | ```text
...
0515 |   manifest.json
0516 |   candidates_all.csv
0517 |   candidates_feasible.csv
0518 |   pareto_3d.csv                 # somente quando F3 elegível
0519 |   convergence.csv
0520 |   dispatch_timeseries.parquet
0521 |   projections/
0522 |   figures/3d/
...
0543 | 
0544 | ## 17. Parecer de consolidação
0545 | 
0546 | A presente especificação **corrige os 24 achados no nível de definição, classificação de lacunas ou imposição de teste**, sem alterar os 137 valores e sem criar hipóteses. O núcleo agregado pode ser programado. A formulação R0–R3 completa permanece **condicionada** a dados e decisões já identificados em B01–B07. Congelar este documento como **baseline de implementação controlada**, não como certificação de modelo científico concluído.
0547 | 
0548 | # ANEXO A — Plano operacional de implementação (fonte consolidada)
0549 | 
0550 | ## 2. Contrato de projeto antes da primeira linha do otimizador
...
0559 |       docs/decisoes.md        # registro de mudança, motivação e aprovação
0560 |       src/d28/io/             # ingestão, schemas, unidades, checksums
0561 |       src/d28/scenarios/      # dias-tipo, cenários, janelas, perfis
0562 |       src/d28/models/         # PV, BESS, CHP, combustível, carregadores, rede
0563 |       src/d28/dispatch/       # MILP Pyomo
0564 |       src/d28/objectives/     # F1/F2/F3 com auditoria independente
0565 |       src/d28/optimization/   # NSGA-II pymoo e tratamento de inviabilidade
0566 |       src/d28/reporting/      # CSV/JSON, gráficos, tabelas do artigo
0567 |       tests/unit/  tests/integration/  tests/physics/  tests/regression/
0568 |       experiments/            # configurações versionadas; seeds
...
0572 | 
0573 | ## 7. Arquitetura de avaliação NSGA-II → MILP
0574 | 
0575 | 1.  Ler e validar o genoma misto, domínios e arquitetura R0–R3.
0576 | 2.  Construir configuração física; rejeitar imediatamente violação de limites geométricos e domínios.
0577 | 3.  Para cada cenário e dia/horizonte exigido, montar MILP com parâmetros imutáveis e resolver com HiGHS.
0578 | 4.  Verificar status ótimo/factível, tolerâncias, balanços e energia não atendida. Se inviável, registrar motivo e vetor de violação; **não produzir F1/F2/F3 falsamente válidos**.
0579 | 5.  Para configuração factível, calcular objetivos em módulo independente do MILP, usando fluxos e fatores com proveniência.
0580 | 6.  Cachear avaliações por hash do vetor, versão de dados, configuração, solver e modelo.
0581 | 7.  Registrar seed, população, gerações, operadores de variáveis mistas, orçamento de avaliações, tolerâncias, timeout e logs. O PC-REV07 não autoriza inventar valores definitivos desses hiperparâmetros: fixá-los em protocolo experimental antes de rodar.
0582 | 
...
0586 | |------|------------------------------------------------------|-----------------------------------------------------------------------------------|
0587 | | M0   | especificação congelada, IDs de equação e dicionário | nenhuma variável/equação sem unidade e fonte; pendências explicitadas             |
0588 | | M1   | ingestão e schemas                                   | 137 IDs únicos, arquivos SHA-256, 5×6720 intervalos, sem NaN não permitido        |
0589 | | M2   | MILP de balanço agregado R0                          | conservação em cada t, PCC ≤ 2500, PV limitada, BESS física                       |
0590 | | M3   | MILP R1/R2/R3                                        | balanços de combustível, CHP e restrições por arquitetura                         |
0591 | | M4   | recarga individual                                   | só após B02: janelas, SOC, gabinetes, continuidade e 100% atendimento             |
0592 | | M5   | F1/F2/F3                                             | F1/F2 independentes; F3 apenas se fronteira ACV fechada ou explicitamente parcial |
0593 | | M6   | NSGA-II                                              | determinismo por seed, tratamento de inviáveis, repetição, convergência           |
0594 | | M7   | publicação científica                                | tabelas auditáveis, incerteza, fronteira ACV, versões e limites declarados        |
0595 | 
0596 | **Política de bloqueios:** B01 e B02 abertos permitem desenvolvimento de M1–M3 sob recorte sintético agregado, mas não M4 nem inferência operacional individual; B03 e B04 impedem conclusões tarifárias/ACV definitivas; B05/B06 exigem mapeamento final para M5; B07 é validado progressivamente por M1–M6.
0597 | 
0598 | ## 9. Testes de regressão e casos mínimos
0599 | 
0600 | - Um intervalo sem PV/CHP/BESS: `P_grid = carga`; acima de 2500 kW deve ser inviável.
0601 | - PV excedente sem exportação: excedente obrigatoriamente cortado ou armazenado.
0602 | - BESS em SOC mínimo não descarrega; em máximo não carrega; carga/descarga simultâneas impossíveis.
0603 | - CHP desligado gera 0; ligado respeita mínimo de 50%; arquitetura R0 proíbe combustível.
0604 | - R2 conserva massa de gás, não consome mais do que estoque e produção; auxiliares não são duplicados.
0605 | - Ônibus indisponível não carrega; saída sem 95% SOC torna caso inviável; dois conectores não duplicam potência de gabinete.
0606 | - `Σ_t P_t Δt` confere com kWh; 70 dias não são tratados como 365 dias sem pesos documentados.
0607 | - F1 testa VPL com exemplo manual; F2 testa máximo sobre intervalo; F3 falha explicitamente se inventário incompleto.
0608 | - Repetir seed+versões gera mesmos resultados dentro de tolerâncias do solver.
0609 | 
0610 | ## 10. GitHub e reprodutibilidade
0611 | 
...
0619 | 
0620 | 1.  Objeto e fronteira do sistema; garagem D28 como caso sintético, não inventário de frota real.
0621 | 2.  Cenários, perfis operacionais, dias-tipo e fontes de dados.
0622 | 3.  Arquiteturas R0–R3 e representação tecnológica.
0623 | 4.  Formulação do problema: índices, parâmetros, variáveis e EQ-001–EQ-017.
0624 | 5.  Acoplamento NSGA-II/MILP, tratamento de inviabilidade, parâmetros experimentais.
0625 | 6.  Fronteiras econômicas e ambientais de F1–F3; exclusões e dados condicionais.
0626 | 7.  Verificação física, validação de software, sensibilidade, convergência e replicação.
0627 | 8.  Limitações B01–B07 e critérios de interpretação de resultados.
0628 | 
0629 | ## 12. Decisões que **não** podem ser silenciosamente preenchidas pelo programador
