"""Module implementing a CHORAS interface for MoDART.
"""
import json
from pathlib import Path
from pprint import pprint

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
        # Load the input JSON file
        with open(self.input_json_path, "r") as json_file:
            result_container = json.load(json_file)
        
        temp_subfolder = Path(result_container['msh_path']).parent / 'MoDART_data'
        result_container['MoDART_data_subfolder'] = str(temp_subfolder)

        print('\n\tDEBUG MESSAGE: reading .msh file at path:')
        print('\t', result_container['msh_path'], '\n')

        with open(result_container['msh_path'], "r") as msh_file:
            for line in msh_file:
                print(line[:-1])
        print()

        print('\n\tDEBUG MESSAGE: creating temp subfolder:')
        print('\t', temp_subfolder, '\n')
        if not Path.is_dir(temp_subfolder):
            Path.mkdir(temp_subfolder)

        obj_path = str(temp_subfolder / 'mesh.obj')
        print('\n\tDEBUG MESSAGE: will write to temp file:')
        print('\t', obj_path, '\n')
        
        import gmsh
        gmsh.initialize()
        try:
            print('\n\tDEBUG MESSAGE: converting mesh to Wavefront format; step 1: load .msh\n')

            gmsh.open(result_container['msh_path'])

            print('\n\tDEBUG MESSAGE: converting mesh to Wavefront format; step 2: save .obj\n')
            
            gmsh.write(obj_path)
        finally:
            gmsh.finalize()
        
        # Save the updated JSON (with the added MoDART_data_subfolder field)
        with open(self.input_json_path, "w") as json_output:
            json_output.write(json.dumps(result_container, indent=4))

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

        print('\n\tDEBUG MESSAGE: starting _modart_method\n')

        obj_path = str(Path(result_container['MoDART_data_subfolder']) / 'mesh.obj')

        print('\n\tDEBUG MESSAGE: reading .obj file at path:')
        print('\t', obj_path, '\n')

        with open(obj_path, "r") as obj_file:
            for line in obj_file:
                print(line[:-1])
        print()

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

        print('\n\tDEBUG MESSAGE: ending _modart_method\n')

        # Save the updated JSON
        with open(json_file_path, "w") as json_output:
            json_output.write(json.dumps(result_container, indent=4))

        print("MoDART simulation completed successfully!")
