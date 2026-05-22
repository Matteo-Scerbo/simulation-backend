"""Test the MoDART method CLI."""
import os
import json
import pytest
import numpy as np

from modart_interface import main


def test_modart_method_cli(mock_requests_post, create_temporary_input_file):
    """Test the MoDART method CLI."""
    # Set JSON_PATH environment variable and call main() directly
    os.environ["JSON_PATH"] = create_temporary_input_file

    main()

    with open(create_temporary_input_file, 'r') as f:
        data = json.load(f)

    assert 'results' in data
    results = data['results']
    assert len(results) > 0
    for res in results:
        assert 'responses' in res
        responses = res['responses']
        assert len(responses) > 0
        for resp in responses:
            assert 'receiverResults' in resp
            rec_res = resp['receiverResults']
            assert rec_res is not None
            assert len(rec_res) > 0
            for r in rec_res:
                assert len(r) == 4
                assert 'data' in r
                assert 't' in r
                assert 'frequency' in r
                assert 'type' in r
                assert r['type'] == 'edc'
                assert len(r['data']) == len(r['t'])

                assert np.all(np.isfinite(r['data']))

    # The function returns a few MoD-ART parameters for debugging/testing.
    assert 'MoDART_data' in data
    MoDART_data = data['MoDART_data']
    assert len(MoDART_data) > 0

    # N.B.: THE FOLLOWING TEST PARAMETERS ARE SPECIFIC TO THE EXAMPLE SETTINGS!

    # The test simulation asks for 2 slopes in 5 frequency bands, so there should be 10.
    assert len(MoDART_data['T60']) == 10
    assert len(MoDART_data['Band idx']) == 10

    # The band indices of the detected slopes should range from 0 to 4,
    #  and there should be exactly two of each.
    unique, unique_counts = np.unique(MoDART_data['Band idx'], return_counts=True)
    assert unique.tolist() == [0, 1, 2, 3, 4]
    assert unique_counts.tolist() == [2, 2, 2, 2, 2]

    # Confirm that the T60 values are reasonably close to a reference run.
    assert np.allclose(MoDART_data['T60'],
                       [0.56, 0.03, 0.32, 0.03, 0.19, 0.03, 0.13, 0.03, 0.1, 0.02],
                       rtol=0.05, atol=0.05)

    # The test room has 6 patches with full visibility, so there should be 6*(6-1)=30 paths.
    # If the second dimension is != 30, that means something went wrong in the mesh decoding.
    assert MoDART_data['Eigenvector shape'] == [10, 30]
    
    # Verify that requests.post was called (save_results was executed)
    mock_requests_post.assert_called_once()


def test_modart_method_cli_missing_json_path(mock_requests_post):
    """Test the MoDART method CLI with missing JSON_PATH."""
    # Clear JSON_PATH environment variable
    if "JSON_PATH" in os.environ:
        del os.environ["JSON_PATH"]

    # Expect FileNotFoundError from SimulationMethod.__init__
    with pytest.raises(FileNotFoundError, match="input_json_path cannot be None or empty"):
        main()
