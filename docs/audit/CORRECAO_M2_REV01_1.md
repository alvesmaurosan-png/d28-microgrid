# Correção controlada REV01.1 — restauração do script de referência M2

Origem: `D28_Otimizacao_PC_REV08_REV01.zip` → `D28_Otimizacao_PC_REV08_REV01/legacy/scripts/02c_compare_pyomo_scipy.py`.
Destino: `scripts/02c_compare_pyomo_scipy.py`.
SHA-256 do arquivo restaurado: `384099a8fdf04ba7d7cd00632b86b1bb5c78e3db53e3f1179f98985d8f5a756c`.

Motivo: o teste `tests/physics/test_m2_scipy_reference.py` importa o script pelo caminho acima, ausente na REV01. Em execução do usuário: 134 testes aprovados, 1 falha FileNotFoundError na coleta do script.

Escopo: somente restauração do script histórico e registro de proveniência. Nenhum módulo do modelo, teste, dado, parâmetro ou protocolo foi alterado.

**Validação pendente:** executar `python -m pytest -q` no ambiente Python 3.11.9 do usuário. Não presumir aprovação de 135 testes antes da execução. Este teste é smoke M2 sintético, não homologação científica.
