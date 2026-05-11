"""CLI module for MoDART method."""
import os
from .modart_interface import MoDARTMethod


def main() -> None:
    """Run the MoDART method simulation."""
    # JSON path in the uploads folder. This variable is set for the
    # container when it is started up.
    json_file_path = os.environ.get("JSON_PATH")

    print(f"Running MoDART method with JSON_PATH={json_file_path}")
    modart_method_object = MoDARTMethod(json_file_path)
    modart_method_object.run_simulation()

    # Save the results to a separate file
    modart_method_object.save_results()

    print("MoDART container finished.")
