import os
import json
import numpy as np
import subprocess
import sys
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
    # Run the CLI without JSON_PATH and expect it to fail
    result = subprocess.run(
        [sys.executable, "-m", "pyroomacoustics_interface"],
        env={**os.environ, "JSON_PATH": ""},
        capture_output=True,
        text=True)

    # Should exit with non-zero status
    assert result.returncode != 0
    # Error message should be in stderr
    assert "JSON_PATH" in result.stderr
    assert "not set or is empty" in result.stderr
