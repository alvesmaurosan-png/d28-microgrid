"""Exemplo sintético integrado: Pyomo/HiGHS + NSGA-II, sem dados D28 homologados."""
import json
from pathlib import Path
from d28.rev02.integration import SyntheticCase, optimize_synthetic


def main():
    result = optimize_synthetic(SyntheticCase(), population=8, generations=2, seed=42)
    output = Path('results/rev02_synthetic_demo.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status':result['status'],'evaluations':result['evaluations'],
        'nondominated_count':len(result['nondominated']), 'output':str(output),
        'classification':result['classification']},ensure_ascii=False,indent=2))
    if result['status']!='PASS_SYNTHETIC_DEMO':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
