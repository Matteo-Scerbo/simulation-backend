import os
import json
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from de_interface import main


@patch("de_interface.definition.requests.post")
def test_de_method_cli(mock_post, create_temporary_input_file):
    """Test the DE method CLI.
    """
    # Mock the requests.post to return a successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    # Set JSON_PATH environment variable and call main() directly
    os.environ["JSON_PATH"] = create_temporary_input_file
    main()

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
