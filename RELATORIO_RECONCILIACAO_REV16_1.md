# Reconciliação REV16.1

Fonte: REV05 (3) e REV16 candidato.

Restaurados 33 scripts/módulos Python ausentes, para preservar dependências. Nenhum conteúdo dos arquivos restaurados foi editado.

Teste duplicado removido: `tests/tests/test_rev06_annual_connector_gate.py` (original idêntico: True).

O manifesto anterior foi regenerado. Esta revisão permanece candidata até os testes passarem.

## Verificação disponível
- A suíte não pôde ser executada neste ambiente porque Pyomo e HiGHS não estão instalados; os erros locais de importação não são um veredito sobre a suíte no Windows.
- Executar `python -m pytest -q --import-mode=importlib` no ambiente `.venv311` do usuário.
- A revisão não está homologada; a execução integrada NSGA-II/MILP R0–R3 continua pendente.
