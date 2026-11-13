# Entrega de integração sintética PC-REV08/REV02

## Escopo
Foi adicionada a interface `d28.rev02.integration` que acopla o NSGA-II REV02 ao MILP Pyomo energético REV02, recupera a potência máxima de importação F2 e calcula um F1 **sintético e parcial**, a partir de componentes econômicos explícitos. Não altera o código herdado.

**Não é o modelo científico completo do protocolo.** A demonstração usa apenas o Cenário 1 sem CHP, oito intervalos artificiais repetidos para representar um ano, e parâmetros econômicos fictícios. Os custos de frota e reforço são definidos como zero **apenas no exemplo**, não como hipótese validada da garagem. O F1 demonstrativo não substitui o F1 integrado homologado. O limite PV 1500 kW é apenas do domínio sintético, não um teto físico aprovado.

## Executar

```powershell
python -m pip install -e .
python -m pytest -q
python .\run_rev02_integrated_demo.py
```

Saída: `results/rev02_synthetic_demo.json`. Dependências Pyomo e HiGHS são necessárias para a execução do exemplo. Os testes que dependem de solver são ignorados automaticamente se indisponível.

## Componentes pendentes (sem implementação simulada)
- Recarga individual, escala e PKM verificado; frota adquirida/disponível/despachada.
- CHP, combustível, topologia elétrica e suprimento de biogás/biometano.
- Cenário 2: frota mista e abastecimento via rede de gás.
- BAU: reforço endógeno de rede e custo associado.
- Custos integrados homologados, séries 15 minutos, evidências B01–B07.

Os contratos dos 12 casos continuam disponíveis em `run_rev02.py`; não confundir geração dos contratos com execução dos 12 MILPs.
