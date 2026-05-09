import json
import numpy as np

from de_interface import DEMethod


def test_acoustic_de(create_temporary_input_file):
    """
    Test the DE acoustic simulation method.
    """
    interface = DEMethod(create_temporary_input_file)
    interface.run_simulation()

    with open(create_temporary_input_file, 'r') as f:
         data = json.load(f)

    rir = np.array(data['results'][0]['responses'][0]['receiverResults'][0][
        "data"
    ])

    assert rir is not None
    assert len(rir) > 0
    assert isinstance(rir, np.ndarray)
    assert np.any(np.abs(rir) >= 1e-6)
