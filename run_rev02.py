"""Diagnóstico de prontidão. Nunca executa MILP automaticamente."""
import json
from pathlib import Path
from d28.rev02.contracts import Scenario, contract
from d28.rev02.readiness import readiness

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    gates = json.loads((root/'config/rev02/evidence_gates.json').read_text())
    for scenario in Scenario:
        for year in (2026,2030,2038):
            print(contract(scenario,year))
    print(json.dumps(readiness(gates),indent=2,ensure_ascii=False))
