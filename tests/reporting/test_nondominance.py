from d28.reporting.pareto import nondominated,triobjective_release_allowed
def test_nondominated():
 rows=[{'id':'a','feasible':True,'F1':1,'F2':3,'F3':2},{'id':'b','feasible':True,'F1':2,'F2':4,'F3':3},{'id':'c','feasible':True,'F1':3,'F2':1,'F3':2},{'id':'d','feasible':False,'F1':0,'F2':0,'F3':0},{'id':'e','feasible':True,'F1':1,'F2':2,'F3':None}]
 assert {r['id'] for r in nondominated(rows)}=={'a','c'}
def test_blocks():
 assert not triobjective_release_allowed({'B04':'ABERTO'})
