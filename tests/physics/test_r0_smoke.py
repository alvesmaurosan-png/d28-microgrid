import pytest
def test_r0_balances():
 p=pytest.importorskip('pyomo.environ')
 from d28.dispatch.milp import build_r0_smoke
 m=build_r0_smoke([100.,150.],[0.,0.5],100.)
 solver=p.SolverFactory('appsi_highs')
 if not solver.available():pytest.skip('HiGHS não instalado')
 solver.solve(m)
 assert abs(p.value(m.grid[0])-100)<1e-6
 assert abs(p.value(m.grid[1])-100)<1e-6
