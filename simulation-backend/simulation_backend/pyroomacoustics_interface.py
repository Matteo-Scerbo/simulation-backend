"""Module implementing a CHORAS interface for pyroomacoustics.
"""
import pyroomacoustics as pra
import gmsh
import numpy as np

from simulation_backend import (
    find_input_file_in_subfolders,
    create_tmp_from_input,
    save_results,
)


def read_json_input(json_file_path):
    """Read the input JSON file.

    Parameters
    ----------
    json_file_path : str
        Path of the input JSON file

    Returns
    -------
    input_data : dict
        Parsed JSON data as a dictionary

    """
    with open(json_file_path, 'r') as f:
        import json
        input_data = json.load(f)

    return input_data


def import_room_geometry(json_file_path):
    """Import room geometry and absorption coefficients.

    The geometry is read from a .geo file specified in the JSON input file.
    The absorption coefficients are directly read from the JSON file.

    Parameters
    ----------
    json_file_path : str
        Path to the JSON file containing room geometry and absorption
        coefficients.

    Returns
    -------
    walls : list of pyroomacoustics.Wall
        List of walls defining the room geometry and boundary conditions for
        all frequency bands.

    Raises
    ------
    ValueError
        If absorption coefficients for any surface are not found in the
        input JSON file.
    """

    with open(json_file_path, 'r') as f:
        import json
        input_data = json.load(f)

    frequencies = input_data['frequencies']
    n_bands = len(frequencies)

    # initialize gmsh and load the geometry file
    gmsh.initialize()
    geometry_file = input_data['geo_path']
    gmsh.open(geometry_file)

    # generate 2d surface mesh
    dim = 2 # 2D surfaces
    gmsh.model.mesh.generate(dim)

    # get all named surfaces in the geometry
    surface_group_tags = gmsh.model.getPhysicalGroups(dim=dim)
    surface_group_names = [
        gmsh.model.getPhysicalName(dim, tag)
        for (dim, tag) in surface_group_tags
    ]

    # get all nodes of the surface mesh
    node_tags_all, coords_all, _ = gmsh.model.mesh.getNodes()
    coords = coords_all.reshape((len(node_tags_all), 3))

    # get the material names from absorption coefficient input
    absorption_names = list(input_data['absorption_coefficients'].keys())

    # check if absorption coefficient data are available for all surfaces
    for name in surface_group_names:
        if name not in absorption_names:
            raise ValueError(
                "Absorption coefficients for surface "
                f"'{name}' not found in input JSON file.")


    # get the element type for surface mesh
    element_type = gmsh.model.mesh.getElementType("triangle", 1)

    # create pyroomacoustics.walls for all surface elements (triangles)
    walls = []

    # loop through all named surfaces and create walls with corresponding
    # absorption and scattering coefficients

    for surface_name in surface_group_names:
        dim_tags = gmsh.model.getEntitiesForPhysicalName(surface_name)
        dim, tag = dim_tags[0]

        face_nodes = gmsh.model.mesh.getElementFaceNodes(
            element_type, 3, tag=tag)
        faces = np.reshape(face_nodes, (len(face_nodes) // 3, 3))

        material = pra.Material(
            energy_absorption={
                'description': surface_name,
                'center_freqs': input_data['frequencies'],
                'coeffs': input_data['absorption_coefficients'][surface_name],
            }
        )

        walls.extend(
            pra.wall_factory(
                coords[face - 1, :].reshape(-1, 3).T,
                absorption=material.energy_absorption['coeffs'],
                scattering=material.scattering['coeffs'],
            )
            for face in faces
        )

    # finalizing gmsh
    gmsh.finalize()

    return walls


def get_source_positions(input_data):
    """Extract source positions from input data.

    Parameters
    ----------
    input_data : dict
        Input data as a dictionary.

    Returns
    -------
    source_positions : np.ndarray
        Array of source positions with shape (3,).
    """
    return np.array([
        input_data['results'][0]['sourceX'],
        input_data['results'][0]['sourceY'],
        input_data['results'][0]['sourceZ'],
    ])


def get_receiver_positions(input_data):
    """Extract receiver positions from input data.

    Parameters
    ----------
    input_data : dict
        Input data as a dictionary.

    Returns
    -------
    receiver_positions : np.ndarray
        Array of receiver positions with shape (n_receivers, 3).
    """

    num_receivers = len(input_data['results'][0]['responses'])

    response_section = input_data['results'][0]['responses']

    receiver_pos = np.zeros((num_receivers, 3), dtype=float)

    for i in range(num_receivers):
        receiver_pos[i] = np.array([
            response_section[i]['x'],
            response_section[i]['y'],
            response_section[i]['z']
        ])

    return receiver_pos


def setup_simulation(json_file_path, walls):
    """Set up the pyroomacoustics simulation based on the JSON file.

    Parameters
    ----------
    json_file_path : str
        Path of the input JSON file
    walls : list of pyroomacoustics.Wall
        List of walls defining the room geometry and boundary conditions

    Returns
    -------
    room : pyroomacoustics.Room
        The configured pyroomacoustics Room object
    """

    print("setup_simulation: setting up simulation")


    input_data = read_json_input(json_file_path)

    sampling_rate = 20000

    room = pra.Room(
        walls,
        fs=sampling_rate,
        max_order=2,
        ray_tracing=True,
        air_absorption=True
    )

    # Add sources
    source_pos = get_source_positions(input_data)
    if source_pos.shape != (3,):
        raise ValueError("Source position must be a 3D coordinate.")
    room.add_source(source_pos)

    receiver_pos = get_receiver_positions(input_data)
    room.add_microphone(receiver_pos.T)

    print("setup_simulation: setup done!")

    return room


def export_rir_to_input(json_file_path, rir):
    """Export the computed RIRs to the input data structure.

    Parameters
    ----------
    input_data : dict
        Input data as a dictionary.
    rir : list of list of np.ndarray
        Computed RIRs from pyroomacoustics.

    Returns
    -------
    None
    """

    with open(json_file_path, 'r') as f:
        import json
        input_data = json.load(f)

    # num_receivers = len(input_data['results'][0]['responses'])

    # for i in range(num_receivers):
    input_data['results'][0]['responses'][0]['receiverResults'] = rir.tolist()

    with open(json_file_path, 'w') as f:
        json.dump(input_data, f, indent=4)


def pyroomacoustics_method(json_file_path=None):
    """Run the simulation method for pyroomacoustics based on the JSON file.

    Parameters
    ----------
    json_file_path : str, optional
        Path of the input JSON file, by default None
    """

    print("pyroomacoustics_method: starting simulation")

    walls = import_room_geometry(json_file_path)

    simulation_setup = setup_simulation(json_file_path, walls)

    # Compute the RIRs
    simulation_setup.compute_rir()

    # Get the RIRs for the first source and first microphone
    rir = simulation_setup.rir[0][0]

    # Example: Save the RIR and reverberant castanets as a WAV file using pyfar
    import pyfar as pf
    rir_pf = pf.Signal(rir, simulation_setup.fs)
    pf.io.write_audio(rir_pf, "example_rir.wav")
    castanets = pf.signals.files.castanets(sampling_rate=simulation_setup.fs)
    castanets_audio = pf.dsp.convolve(rir_pf, castanets, mode="full")
    pf.io.write_audio(castanets_audio, "reverberant_castanets.wav")

    export_rir_to_input(json_file_path, rir)

    print("pyroomacoustics_method: simulation done!")


if __name__ == "__main__":
    import os

    from simulation_backend import (
        find_input_file_in_subfolders,
        create_tmp_from_input,
        save_results,
    )

    # Load the input file
    file_name = find_input_file_in_subfolders(
        os.path.dirname(__file__), "exampleInput_pyroomacoustics.json"
    )
    json_tmp_file = create_tmp_from_input(file_name)

    # Run the method
    print(f"Created temporary settings file: {json_tmp_file}")
    pyroomacoustics_method(json_tmp_file)

    # Save the results to a separate file
    save_results(json_tmp_file)
