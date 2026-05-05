import os
import gmsh
import json
import numpy as np

from dg_interface import DGMethod


def test_edg_acoustics(create_temporary_input_file):
    """
    Test the DG acoustic simulation method.
    """
    gmsh.initialize()
    interface = DGMethod(create_temporary_input_file)
    interface.run_simulation()
    gmsh.finalize()

    with open(create_temporary_input_file, 'r') as f:
        data = json.load(f)

    rir = np.array(data['results'][0]['responses'][0]['receiverResults'])

    assert rir is not None
    assert len(rir) > 0
    assert isinstance(rir, np.ndarray)
    assert np.any(np.abs(rir) >= 1e-6)
