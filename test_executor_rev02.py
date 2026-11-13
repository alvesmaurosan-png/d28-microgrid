import json
import tempfile
import unittest
from pathlib import Path
from executar_matriz_rev02 import build

class TestMatrix(unittest.TestCase):
    def test_48_blocked_without_fake_objectives(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'config/rev02').mkdir(parents=True)
            (root/'config/rev02/scenarios.json').write_text(json.dumps({
                'protocol':'PC-REV08/REV02','status':'PROPOSED_NOT_HOMOLOGATED',
                'total_fleet':450,'years':{'2026':100,'2030':300,'2038':450},
                'scenarios':['BAU','Realista','Cenario_1','Cenario_2']}))
            rows, summary=build(root)
            self.assertEqual(len(rows),48)
            self.assertEqual(summary['executed'],0)
            self.assertTrue(all(not r['F1_brl_per_pkm'] and not r['F2_kw'] for r in rows))
            self.assertTrue(all(r['pcc_limit_kw']=='' for r in rows if r['scenario']=='BAU'))
            self.assertTrue(all(r['pcc_limit_kw']==2500 for r in rows if r['scenario']!='BAU'))

if __name__=='__main__': unittest.main()
