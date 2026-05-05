"""Test the pyroomacoustics simulation backend.
"""
import os
import json
import numpy as np
import numpy.testing as npt

import pyroomacoustics_interface as pra_interface


def test_get_receiver(default_input_data):
    """Test the get_receiver function."""
    receiver = pra_interface.get_receiver_positions(default_input_data)

    assert receiver is not None
    npt.assert_array_equal(receiver, np.array([[1.0, 1.0, 1.5]]))


def test_get_source_positions(default_input_data):
    """Test the get_source_positions function."""
    sources = pra_interface.get_source_positions(default_input_data)

    assert sources is not None
    npt.assert_array_equal(sources, np.array([2.0, 2.0, 1.5]))


def test_export_rir_to_input(create_temporary_input_file):
    """Test the export_rir_to_input function."""
    rir = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], dtype=float)
    pra_interface.export_rir_to_input(create_temporary_input_file, rir)

    with open(create_temporary_input_file, 'r') as f:
        data = json.load(f)

    npt.assert_array_equal(
        data['results'][0]['responses'][0]['receiverResults'], rir)


def test_run_simulation(create_temporary_input_file):
    """Run the full simulation pipeline."""
    interface = pra_interface.PyroomacousticsMethod(create_temporary_input_file)
    interface.run_simulation()

    with open(create_temporary_input_file, 'r') as f:
        data = json.load(f)

    rir = np.array(data['results'][0]['responses'][0]['receiverResults'])

    assert rir is not None
    assert len(rir) > 0
    assert isinstance(rir, np.ndarray)
    assert np.any(np.abs(rir) >= 1e-6)


def test_pyroomacoustics_method_cli(create_temporary_input_file):
    """Test the Pyroomacoustics method CLI."""
    # Simulate running the CLI by setting the environment variable and
    # calling the main function
    os.environ["JSON_PATH"] = create_temporary_input_file

    # Run the main function
    os.system("python -m pyroomacoustics_interface")

    with open(create_temporary_input_file, 'r') as f:
        data = json.load(f)

    rir = np.array(data['results'][0]['responses'][0]['receiverResults'])

    assert rir is not None
    assert len(rir) > 0
    assert isinstance(rir, np.ndarray)
    assert np.any(np.abs(rir) >= 1e-6)
