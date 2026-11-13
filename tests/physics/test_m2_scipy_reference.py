import importlib.util
from pathlib import Path
import numpy as np

def test_scipy_reference_solution():
    path=Path(__file__).resolve().parents[2]/'scripts/02c_compare_pyomo_scipy.py'
    spec=importlib.util.spec_from_file_location('m2compare',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    s=module.scipy_solve()
    np.testing.assert_allclose(s['grid_kw'],[100.,120.,70.,70.],atol=1e-6)
    np.testing.assert_allclose(s['pv_kw'],[0.,30.,50.,10.],atol=1e-6)
    assert abs(module.validate(s)['grid_energy_kwh']-90.)<1e-6
