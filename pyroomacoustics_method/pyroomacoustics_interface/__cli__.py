import os
from .pyroomacoustics_interface import PyroomacousticsMethod
import gmsh


def main() -> None:
    """Run the Pyroomacoustics method simulation."""
    # JSON path in the uploads folder. This variable is set for the
    # container when it is started up.
    json_file_path = os.environ.get("JSON_PATH")

    print(f"Running Pyroomacoustics method with JSON_PATH={json_file_path}")
    pyroomacoustics_method_object = PyroomacousticsMethod(json_file_path)
    pyroomacoustics_method_object.run_simulation()

    # Save the results to a separate file
    pyroomacoustics_method_object.save_results()

    print("Pyroomacoustics container finished.")
