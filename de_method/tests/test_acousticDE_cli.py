import os
import json
import numpy as np
import subprocess
import sys


def test_de_method_cli(create_temporary_input_file):
    """Test the DE method CLI.
    """
    # Simulate running the CLI by setting the environment variable and
    # calling the main function
    subprocess.run(
        [sys.executable, "-m", "de_interface"],
        check=True,
        env={**os.environ, "JSON_PATH": create_temporary_input_file})

    with open(create_temporary_input_file, 'r') as f:
        data = json.load(f)

    rir = np.array(data['results'][0]['responses'][0]['receiverResults'][0][
        "data"
    ])

    assert rir is not None
    assert len(rir) > 0
    assert isinstance(rir, np.ndarray)
    assert np.any(np.abs(rir) >= 1e-6)

    # Verify that requests.post was called (save_results was executed)
    mock_post.assert_called_once()
