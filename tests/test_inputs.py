from pathlib import Path
from d28.inputs import audit
def test_m1_structural():
 r=audit(Path(__file__).resolve().parents[1]);assert not r['errors'];assert r['parameter_count']==137;assert not r['scientific_release_allowed']
