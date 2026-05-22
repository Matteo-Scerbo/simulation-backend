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

    assert 'receiverResults' in data['results'][0]['responses'][0]
    results = data['results'][0]['responses'][0]['receiverResults']
    assert results is not None
    assert len(results) > 0
    for r in results:
        assert len(r) == 4
        assert 'data' in r
        assert 't' in r
        assert 'frequency' in r
        assert 'type' in r
        assert r['type'] == 'edc'
        assert len(r['data']) == len(r['t'])

        assert np.all(np.isfinite(r['data']))

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
