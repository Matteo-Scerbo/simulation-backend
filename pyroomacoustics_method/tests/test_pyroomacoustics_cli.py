import os
import json
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from pyroomacoustics_interface import main


@patch("pyroomacoustics_interface.definition.requests.post")
def test_pyroomacoustics_method_cli(mock_post, create_temporary_input_file):
    """Test the Pyroomacoustics method CLI."""
    # Mock the requests.post to return a successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    # Set JSON_PATH environment variable and call main() directly
    os.environ["JSON_PATH"] = create_temporary_input_file
    main()

    with open(create_temporary_input_file, 'r') as f:
        data = json.load(f)

    rir = np.array(data['results'][0]['responses'][0]['receiverResults'])

    assert rir is not None
    assert len(rir) > 0
    assert isinstance(rir, np.ndarray)
    assert np.any(np.abs(rir) >= 1e-6)

    # Verify that requests.post was called (save_results was executed)
    mock_post.assert_called_once()


def test_pyroomacoustics_method_cli_missing_json_path():
    """Test the Pyroomacoustics method CLI with missing JSON_PATH."""
    # Set JSON_PATH to empty string
    os.environ["JSON_PATH"] = ""

    # Expect SystemExit with code 1
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
