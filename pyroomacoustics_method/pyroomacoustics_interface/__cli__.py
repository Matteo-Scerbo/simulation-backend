import os
import sys
from .pyroomacoustics_interface import PyroomacousticsMethod


def main() -> None:
    """Run the Pyroomacoustics method simulation."""
    # JSON path in the uploads folder. This variable is set for the
    # container when it is started up.
    json_file_path = os.environ.get("JSON_PATH")

    if not json_file_path:
        print(
            "Error: JSON_PATH environment variable is not set or is empty.",
            file=sys.stderr
        )
        sys.exit(1)

    print(f"Running Pyroomacoustics method with JSON_PATH={json_file_path}")
    pyroomacoustics_method_object = PyroomacousticsMethod(json_file_path)
    pyroomacoustics_method_object.run_simulation()

    # Save the results to a separate file
    pyroomacoustics_method_object.save_results()

    print("Pyroomacoustics container finished.")
