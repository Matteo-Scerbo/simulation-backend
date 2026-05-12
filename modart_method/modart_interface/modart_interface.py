"""Module implementing a CHORAS interface for MoDART.
"""
import json
import meshio
import numpy as np
from pathlib import Path

from raves import raves, run_MoDART

from numpy.random import default_rng
from scipy.signal import butter, sosfilt
from scipy.interpolate import make_interp_spline

from .definition import SimulationMethod


def convert_mesh(input_file_path: str | Path | None = None,
                 output_folder_path: str | Path | None = None):
    if type(output_folder_path) == str:
        output_folder_path = Path(output_folder_path)

    mesh = meshio.read(input_file_path)

    vertices = np.array(mesh.points).squeeze()
    num_vertices = vertices.shape[0]

    # TODO: Take care: if the number of triangles is the same as the number of some other type of element, the material retrieval will fail.

    # TODO: Ensure that the mesh is triangulated.

    triangles = np.array([cell.data for cell in mesh.cells
                            if cell.type == "triangle"]).squeeze()
    num_triangles = triangles.shape[0]

    # N.B.: the triangle normals are inverted w.r.t. what MoD-ART expects. Flip them.
    triangles = triangles[:, ::-1]

    assert np.all(triangles < num_vertices), 'The triangle definitions include vertex indices out of range.'

    material_ids = np.array([l for l in mesh.cell_data['gmsh:physical']
                                if len(l) == num_triangles]).squeeze()

    material_names = dict()
    for k, [mat_idx, n_dims] in mesh.field_data.items():
        if n_dims == 2:
            material_names[mat_idx] = k

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
    
    with open(str(output_folder_path / 'mesh.obj'), mode='w') as file:
        for line in obj_output_lines:
            file.write(line)
    with open(str(output_folder_path / 'mesh.mtl'), mode='w') as file:
        for line in mtl_output_lines:
            file.write(line)


def save_materials_file(json_file_path: str | Path):
    # Load the input JSON file
    with open(json_file_path, "r") as json_file:
        result_container = json.load(json_file)
    
    # TODO: For now we assume that the length of each
    #           result_container['absorption_coefficients'].values()
    #       is the same as the length of each
    #           result_container['results'][res_idx]['frequencies']
    #       Eventually this will change.
    freq_bands = None
    for res in result_container['results']:
        freqs = np.array(res['frequencies'], dtype=float)
        if freq_bands is None:
            freq_bands = freqs
        else:
            assert len(freq_bands) == len(freqs)
    
    absorptions = dict()
    for material, coeff_string in result_container['absorption_coefficients'].items():
        coeffs = np.array(coeff_string.replace(',', '').split(' '), dtype=float)
        if freq_bands is None:
            raise RuntimeError('The frequencies should be known before the coefficients are read.')
        else:
            assert len(freq_bands) == len(coeffs)
            absorptions[material] = coeffs
    
    with open(str(Path(result_container['MoDART_data_subfolder']) / 'materials.csv'), mode='w') as file:
        line = 'Frequencies, ' + ', '.join([str(f) for f in freq_bands]) + '\n'
        file.write(line)

        for material, coeffs in absorptions.items():
            line = material + ', ' + ', '.join([str(c) for c in coeffs]) + '\n'
            file.write(line)

            # TODO: For now, scattering coefficients are arbitrarily set to 0.3.
            #       Eventually they will be sent by the backend.
            line = material + ', 0.3\n'
            file.write(line)


def noise_shaping(fs: int | float, duration_in_samples: int,
                  frequencies: np.ndarray, envelopes: np.ndarray):
    assert frequencies.ndim == 1
    assert envelopes.ndim == 4
    assert envelopes.shape[2] == frequencies.shape[0]

    # Random number generator for the stochastic signal to be modulated.
    rng = default_rng()
    
    # White noise
    #   noise_signal = rng.normal(size=duration_in_samples)
    # Poisson process
    noise_signal = rng.poisson(lam=0.5, size=duration_in_samples).astype(float)

    # Ensure the noise signal has unit energy per second, matching the
    #   convention used to generate the echograms.
    noise_signal *= np.sqrt(duration_in_samples * fs / np.sum(noise_signal**2))
    
    # Factor for octave-band boundaries.
    # TODO: These may become third-octave bands at some point.
    band_bound = np.sqrt(2)
    # Consider the frequency band centers provided alongside the input data.
    band_centers = frequencies.copy()
    num_bands = len(band_centers)
    
    # Ensure that all frequencies support band-pass filtering.
    if np.any(band_centers * band_bound >= fs):
        print('Warning: the audio sample rate is too low for some frequency bands.')
        # Select only acceptable bands.
        band_centers = band_centers[band_centers * band_bound < fs]
        # Update the number of rendered bands.
        num_bands = len(band_centers)
        # Drop unused bands from the echogram, to preserve the right shape.
        envelopes = envelopes[:, :, :num_bands]
    
    # Prepare an array for the band-pass filtered signals.
    filtered_noise_signals = np.zeros((num_bands, duration_in_samples))
    
    for b in range(num_bands):
        # Prepare the suitable band-pass filter...
        sos = butter(6, (band_centers[b] / band_bound,
                         band_centers[b] * band_bound),
                    btype='bandpass', output='sos', fs=fs)
        # ...and apply it to the stochastic signal.
        filtered_noise_signals[b] = sosfilt(sos, noise_signal)
    
    # The envelope array has shape (S, L, B, T), the noise signals have shape (B, T):
    #   we need to add two "leading" dimensions, which is done using [None, None].
    modulated_noise_signals = envelopes * filtered_noise_signals[None, None]
    
    # The dimension of index 2 holds the separate frequency bands.
    # Sum the array along that dimension to obtain the complete room impulse responses.
    return np.sum(modulated_noise_signals, axis=2)


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
        
        # Create a folder for the "temporary" ART and MoD-ART data.
        temp_subfolder = Path(result_container['msh_path']).parent / 'MoDART_data'
        result_container['MoDART_data_subfolder'] = str(temp_subfolder)
        if not Path.is_dir(temp_subfolder):
            Path.mkdir(temp_subfolder)
        
        # Save the updated JSON (with the added MoDART_data_subfolder field)
        with open(self.input_json_path, "w") as json_output:
            json_output.write(json.dumps(result_container, indent=4))

        # This was used to create a simplified "toy example" mesh for testing.
        """
        import gmsh
        gmsh.initialize()
        try:
            gmsh.open('C:/Users/matte/Desktop/CHORAS/simulation-backend/modart_method/tests/test_room_modart.geo')
            gmsh.option.setNumber('Mesh.MeshSizeFactor', 6.0)
            gmsh.option.setNumber('Mesh.SaveAll', 0)
            gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
            gmsh.model.mesh.generate(2)
            gmsh.write('C:/Users/matte/Desktop/CHORAS/simulation-backend/modart_method/tests/test_room_modart_simple.msh')
        finally:
            gmsh.finalize()
        return
        """

        # Convert the .msh file into the format expected by MoD-ART.
        convert_mesh(result_container['msh_path'], temp_subfolder)

        # Save the material information into the .csv file expected by MoD-ART.
        save_materials_file(self.input_json_path)
        
        # Run MoD-ART.
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
        
        environment_folder = result_container['MoDART_data_subfolder']
        # TODO: this will eventually be named differently in the JSON.
        response_duration = result_container['simulationSettings']['de_ir_length']
        
        # TODO: Load and use simulation settings.

        # TODO: echogram_sample_rate will eventually be a parameter set by the user.
        echogram_sample_rate = int(1e3)
        # TODO: audio_sample_rate will eventually be a parameter set by...?
        audio_sample_rate = int(44.1e3)

        # Run the pre-processing (shared by all sources, listeners).
        # TODO: Update progress bar.
        raves(environment_folder)

        for sim_idx, sim_dict in enumerate(result_container['results']):
            source_position = np.array([sim_dict['sourceX'],
                                        sim_dict['sourceY'],
                                        sim_dict['sourceZ']])
            listener_positions = np.array([[pos['x'], pos['y'], pos['z']]
                                           for pos in sim_dict['responses']])

            # Generate the echograms with MoD-ART.
            MoDART_echograms, frequencies, _ = run_MoDART(environment_folder,
                                                          source_position, listener_positions,
                                                          echogram_duration=response_duration,
                                                          echogram_sample_rate=echogram_sample_rate)
            
            # Prepare the audio-rate time intervals at which we'll evaluate the upsampled echogram.
            echogram_time_axis = np.arange(0, response_duration, 1 / echogram_sample_rate)
            audio_time_axis = np.arange(0, response_duration, 1 / audio_sample_rate)
            # We use a linear interpolation, because any other upsampling algorithm risks introducing negative values.
            linear_spline = make_interp_spline(echogram_time_axis, MoDART_echograms, k=1, axis=-1)
            upsampled_echograms = linear_spline(audio_time_axis)
            
            # Normalize w.r.t. the new sample rate, to preserve the energy-per-second definition of echogram values.
            upsampled_echograms *= echogram_sample_rate / audio_sample_rate
                    
            # Translate the energy envelopes to amplitude envelopes.
            envelopes = np.sqrt(upsampled_echograms)

            # Amplitude-modulate band-passed stochastic signals to produce an impulse response.
            responses = noise_shaping(audio_sample_rate, len(audio_time_axis),
                                      frequencies, envelopes)
            
            # Write results back to JSON.
            for rec_idx in range(len(listener_positions)):
                # Note that the first index of "responses" is for the single source position.
                result_container['results'][sim_idx]['responses'][rec_idx]['receiverResults'] = responses[0, rec_idx].tolist()

        # Save the updated JSON
        with open(json_file_path, "w") as json_output:
            json_output.write(json.dumps(result_container, indent=4))

        print("MoDART simulation completed successfully!")
