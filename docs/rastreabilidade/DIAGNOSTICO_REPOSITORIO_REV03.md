# D28 — Diagnóstico de organização e transição para publicação

## Escopo
Auditoria estática do ZIP fornecido. Nenhum teste MILP anual ou pytest foi executado neste ambiente. Esta entrega é um **candidato de organização compatível**, não uma versão científica homologada.

## Constatações objetivas
- O ZIP contém código e testes já organizados em `src/d28` e `tests`, além de muitos scripts históricos na raiz e em `scripts`.
- `README.md` atual descreve a matriz REV02 de 48 células bloqueadas; não descreve o executor R0/E100 REV16.1.4b como interface pública principal.
- `config/rev02/scenarios.json` contém apenas um número de ônibus por ano (2026:100, 2030:300, 2038:450), incompatível com os **dois** cenários de 2026 agora aprovados. Além disso, mistura a classificação BAU/Realista/C1/C2 com o eixo de frota. NÃO foi sobrescrito para evitar quebrar código antigo.
- O protocolo DOCX do pacote é anterior à REV03. A versão REV03 foi incluída como novo arquivo e deve ser promovida após conferência documental.
- `rev16_1_4/` já contém o executor e a busca NSGA-II exploratória, mas eles ainda não estão integrados a `scripts/run_experiment.py`. Criar um invólucro oficial sem verificar as dependências poderia alterar o comportamento.
- Existem cópias byte-a-byte de séries grandes em `data/processed/annual_charging` e `data/processed/charging`; foram **mantidas** nesta entrega para preservar referências existentes.
- O pacote inclui resultados e evidências anteriores. Não há base para declarar os resultados exploratórios como homologados.

## Decisões de organização adotadas
1. Preservar os caminhos atuais de `src`, `tests`, `scripts`, `config`, `data`, `results` e `rev16_1_4` nesta etapa.
2. Remover somente cache de Python e arquivos de IDE; separar backups e pacotes ZIP aninhados num arquivo histórico à parte.
3. Adicionar `config/scenarios/pc_rev08_rev03_matrix.json` sem sobrescrever o contrato REV02.
4. Incorporar o PC-REV08/REV03 como documento de referência, sem apagar o protocolo anterior.
5. Adicionar inventário SHA-256 e registro das duplicatas para orientar uma futura deduplicação **após** testes de equivalência.

## Passos antes de uma versão pública definitiva
- Reconciliar a nomenclatura dos cenários (E100/E200/E300/E450) com BAU/Realista/C1/C2 e arquiteturas R0–R3, preservando dimensões independentes.
- Fazer a transição dos scripts REV16.1.4 para um único `scripts/run_experiment.py` somente após testes de regressão.
- Criar manifestos por execução com hash dos dados, commit, versões, seed, status real do solver, gap e elegibilidade.
- Definir quais séries podem ser redistribuídas e documentar origens e licenças; remover dados sensíveis se houver.
- Executar testes e reproduzir o ponto R0/E100 F1≈0,120108566 R$/PKM e F2≈861,374287 kW, sem presumir certificação de otimalidade.
- Não publicar um arquivo `pareto_3d.csv` como saída vigente; F3 é indicador complementar, não função-objetivo.

## Uso da entrega
O arquivo `D28_REPOSITORIO_CANDIDATO_ORGANIZADO.zip` é uma cópia conservadora com caminhos de execução preservados. **Não substitua o diretório original** até concluir os testes locais. O arquivo `D28_ARQUIVO_HISTORICO_SEPARADO.zip` guarda material segregado.
