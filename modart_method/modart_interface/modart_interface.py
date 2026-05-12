"""Module implementing a CHORAS interface for MoDART.
"""
import json
import numpy as np
from pathlib import Path

from raves.src.utils import visualize_mesh

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

        print('\tDEBUG MESSAGE: reading .msh file at path:')
        print('\t', result_container['msh_path'], '\n')

        print('\tDEBUG MESSAGE: creating temp subfolder:')
        print('\t', temp_subfolder, '\n')
        if not Path.is_dir(temp_subfolder):
            Path.mkdir(temp_subfolder)

        """
        import gmsh
        gmsh.initialize()
        try:
            gmsh.open(result_container['msh_path'])
            # Doing this does not include the materials.
            gmsh.write(obj_path)
        finally:
            gmsh.finalize()
        """
        
        print('\tDEBUG MESSAGE: loading mesh using meshio')
        import meshio
        mesh = meshio.read(result_container['msh_path'])

        vertices = np.array(mesh.points).squeeze()
        num_vertices = vertices.shape[0]
        print('\tDEBUG MESSAGE: num vertices:', num_vertices)
        print('\tDEBUG MESSAGE: first vertex:', vertices[0])

        # TODO: Take care: if the number of triangles is the same as the number of some other type of element, the material retrieval will fail.
        # TODO: Ensure that the mesh is triangulated.

        triangles = np.array([cell.data for cell in mesh.cells
                              if cell.type == "triangle"]).squeeze()
        num_triangles = triangles.shape[0]
        print('\tDEBUG MESSAGE: num triangles:', num_triangles)
        print('\tDEBUG MESSAGE: first triangle:', triangles[0])

        assert np.all(triangles < num_vertices), 'The triangle definitions include vertex indices out of range.'

        material_ids = np.array([l for l in mesh.cell_data['gmsh:physical']
                                 if len(l) == num_triangles]).squeeze()
        print('\tDEBUG MESSAGE: materials:', material_ids)

        material_names = dict()
        for k, [mat_idx, n_dims] in mesh.field_data.items():
            if n_dims == 2:
                material_names[mat_idx] = k
                print('\tDEBUG MESSAGE: field_data:', mat_idx, k)
        print()

        # Doing this does not include the materials.
        # mesh.write(obj_path)
        
        print('\tDEBUG MESSAGE: beginning .obj/.mtl assembly')
        obj_output_lines = list()
        mtl_output_lines = list()

        obj_output_lines.append('mtllib mesh.mtl\n')
    
        for v in vertices:
            rounded_coords = [np.round(c, 3) for c in v]
            line = 'v ' + ' '.join([str(c) for c in rounded_coords]) + '\n'
            obj_output_lines.append(line)
        for i in range(num_triangles):
            patch_name = f'Patch_{i+1}_Mat_{material_names[material_ids[i]]}'

            obj_output_lines.append(f'usemtl {patch_name}\n')
            obj_output_lines.append('f ' + ' '.join([str(v+1) for v in triangles[i]]) + '\n')
            
            mtl_output_lines.append(f'newmtl {patch_name}\n')
            rand_color = np.round(np.random.uniform(size=3), 3)
            mtl_output_lines.append(f'Kd {rand_color[0]} {rand_color[1]} {rand_color[2]}\n')
        
        # print('\n')
        # for line in obj_output_lines:
        #     print(line[:-1])
        # print('\n')
        
        # print('\n')
        # for line in mtl_output_lines:
        #     print(line[:-1])
        # print('\n')

        obj_path = str(temp_subfolder / 'mesh.obj')
        mtl_path = str(temp_subfolder / 'mesh.mtl')
        print('\tDEBUG MESSAGE: will write to temp files:')
        print('\t\t', obj_path)
        print('\t\t', mtl_path)
        
        with open(obj_path, mode='w') as file:
            for line in obj_output_lines:
                file.write(line)
        with open(mtl_path, mode='w') as file:
            for line in mtl_output_lines:
                file.write(line)
        
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

        print('\tDEBUG MESSAGE: starting _modart_method\n')

        visualize_mesh(result_container['MoDART_data_subfolder'])

        # raves(result_container['MoDART_data_subfolder'])

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

        print('\tDEBUG MESSAGE: ending _modart_method\n')

        # Save the updated JSON
        with open(json_file_path, "w") as json_output:
            json_output.write(json.dumps(result_container, indent=4))

        print("MoDART simulation completed successfully!")
