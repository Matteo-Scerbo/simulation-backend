# This is the example interface file for connecting CHORAS to your simulation method

# Import the relevant functions from your package (/submodule)
from My_New_Method import simulation_method
from simulation_method_interface import SimulationMethod


# This function will be called from the main function below, while it runs
# in the container. The container is started in backend/app/simulation_service. 

class MyNewMethod(SimulationMethod):
    def __init__(self):
        super().__init__()

    def run_simulation(self, json_file_path: str):
        self._mynewmethod_method(json_file_path)

    def _mynewmethod_method(self, json_file_path=None):

        print("mynewmethod_method: starting simulation")

        # Call the appropriate function(s) in your package to simulate
        simulation_method(json_file_path)

        print("mynewmethod_method: simulation done!")


if __name__ == "__main__":
    import os

    from HelperFunctions import (
        save_results
    )
    
    json_file_path = os.environ.get("JSON_PATH")
    
    print(f"Running MyNewMethod method with JSON_PATH={json_file_path}")

    # Run the method
    my_new_method = MyNewMethod()
    my_new_method.run_simulation(json_file_path)

    # Save the results to a separate file
    save_results(json_file_path)
