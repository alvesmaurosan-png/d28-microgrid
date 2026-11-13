# D28 — Repositório limpo REV16 (candidato)

**Estado:** limpeza estrutural, NÃO é homologação do NSGA-II + MILP R0–R3.

Fonte: `D28_REPOSITORIO_INTEGRADO_REV05 (3).zip`. Arquivos preservados: 276.

## Organização
- `src/d28/`: implementação do modelo.
- `config/`: contratos, parâmetros e hipóteses.
- `data/`: entradas e rastreabilidade (incluindo duplicatas conservadas quando não comprovada sua substituibilidade).
- `tests/`: testes de regressão e integração.
- `scripts/`: entradas operacionais e verificações selecionadas.
- `docs/`: protocolo, formulação, metodologia, auditoria e rastreabilidade.
- `experiments/`: manifestos de experimentos.

## Excluído
Arquivos `.idea`, caches Python/pytest, backups, relatórios e resultados gerados, scripts auxiliares legados e arquivos avulsos históricos da raiz. Não foram alterados os arquivos mantidos.

## Reproduzir e testar
Em PowerShell na raiz extraída:
```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONPATH = 'src'
python -m pytest -q
python scripts\14_limiar_estrutural_pcc.py --scenario E100
python scripts\15_sensibilidade_bess.py --scenario E100 --bess-kwh 10950 --pcs-kw 5500
```
Os comandos de otimização anual devem ser executados somente após validação dos testes e contratos de R0–R3 e F1–F2.

## Limites
A limpeza foi realizada por inventário de caminhos, sem execução do conjunto de testes no Windows. Alguns scripts legados excluídos podem ser requeridos por testes ou documentação histórica; a versão original deve ser mantida como arquivo de auditoria. O manifesto SHA-256 lista cada arquivo incluído.
