"""CLI module for DE method."""
import os
from .DEinterface import DEMethod


def main() -> None:
    """Run the DE method simulation."""
    # JSON path in the uploads folder. This variable is set for the
    # container when it is started up.
    json_file_path = os.environ.get("JSON_PATH")

    print(f"Running DE method with JSON_PATH={json_file_path}")
    de_method_object = DEMethod(json_file_path)
    de_method_object.run_simulation()

    # Save the results to a separate file
    de_method_object.save_results()

    print("DE container finished.")
