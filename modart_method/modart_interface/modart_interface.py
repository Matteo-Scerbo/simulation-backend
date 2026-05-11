"""Module implementing a CHORAS interface for MoDART.
"""
import json
from pathlib import Path

from .definition import SimulationMethod


class MoDARTMethod(SimulationMethod):
    """Interface class to run the MoDART method.

    The class implements method to run the calculations for the
    MoDART simulation method. All required configuration parameters
    are expected to be provided in the input JSON file passed during
    initialization.

    """

    def __init__(self, input_json_path: str | Path | None = None):
        """Initialize the MoDART method interface for the given JSON file."""
        super().__init__(input_json_path)

    def run_simulation(self) -> None:
        """Run the simulation.

        Parameters
        ----------
        json_file_path : str | Path | None, optional
            Path to the JSON file. If not provided, uses the path from initialization.
        """
        self._modart_method(self.input_json_path)

    def _modart_method(self, json_file_path: str | Path) -> None:
        """
        Run MoDART simulation for acoustic wave propagation.

        Args:
            json_file_path: Path to the JSON configuration file
        """
        # Load the input JSON file
        with open(json_file_path, "r") as json_file:
            result_container = json.load(json_file)

        print('\tDEBUG MESSAGE: running _modart_method')

        # TODO: Implement your simulation logic here
        # 1. Extract simulation parameters from result_container
        # 2. Run your simulation
        # 3. Process results
        # 4. Write results back to result_container

        # Example structure (modify based on your needs):
        # simulation_settings = result_container["simulationSettings"]
        # source_coords = [
        #     result_container["results"][0]["sourceX"],
        #     result_container["results"][0]["sourceY"],
        #     result_container["results"][0]["sourceZ"],
        # ]
        # receiver_coords = [
        #     result_container["results"][0]["responses"][0]["x"],
        #     result_container["results"][0]["responses"][0]["y"],
        #     result_container["results"][0]["responses"][0]["z"],
        # ]

        # Run your simulation here
        # results = your_simulation_function(...)

        # Write results back to JSON
        # result_container["results"][0]["responses"][0]["receiverResults"] = results.tolist()

        # Save the updated JSON
        with open(json_file_path, "w") as json_output:
            json_output.write(json.dumps(result_container, indent=4))

        print("MoDART simulation completed successfully!")
