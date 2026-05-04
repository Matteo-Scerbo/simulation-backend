import os
from .DGinterface import DGMethod
import gmsh

def main() -> None:
    """Run the DG method simulation."""
    # JSON path in the uploads folder. This variable is set for the
    # container when it is started up.
    json_file_path = os.environ.get("JSON_PATH")

    print(f"Running DG method with JSON_PATH={json_file_path}")
    gmsh.initialize()
    dg_method_object = DGMethod(json_file_path)
    dg_method_object.run_simulation()
    gmsh.finalize()

    # Save the results to a separate file
    dg_method_object.save_results()

    print("DG container finished.")
