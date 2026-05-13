"""Module implementing a CHORAS interface for MoDART.
"""
import re
import json
import meshio
import numpy as np
from pprint import pprint
from pathlib import Path

import matplotlib.pyplot as plt

from raves import raves, run_MoDART
from raves.src.utils import visualize_mesh

from numpy.random import default_rng
from scipy.signal import butter, sosfilt
from scipy.interpolate import make_interp_spline

from .definition import SimulationMethod


# TODO: This function exists in "raves" but it not exposed. Perhaps it should be.
def sanitize_ascii(s: str) -> str:
    return re.sub(r'[\W_]+', '_', s, flags=re.ASCII).strip('_')



def convert_mesh(input_file_path: str | Path | None = None,
                 output_folder_path: str | Path | None = None):
    if type(output_folder_path) == str:
        output_folder_path = Path(output_folder_path)

    # TODO: Ensure that the mesh is triangulated.
    
    mesh = meshio.read(input_file_path)

    vertices = np.array(mesh.points).squeeze()
    num_vertices = vertices.shape[0]

    triangles = list()
    triangle_cell_ids = list()
    triangle_group_ids = list()
    num_groups = 0
    for cell_id, cell in enumerate(mesh.cells):
        if cell.type == 'triangle':
            group = cell.data

            if group.ndim == 1:
                assert group.shape[0] == 3, 'Bad cell shape.'
                triangles.append(group)
                triangle_cell_ids.append(cell_id)
                triangle_group_ids.append(num_groups)

            elif group.ndim == 2:
                assert group.shape[1] == 3, 'Bad cell shape.'
                for tri in group:
                    triangles.append(tri)
                    triangle_cell_ids.append(cell_id)
                    triangle_group_ids.append(num_groups)
            else:
                raise AssertionError('Bad cell shape.')

            num_groups += 1
    
    triangles = np.array(triangles)
    num_triangles = triangles.shape[0]
    triangle_cell_ids = np.array(triangle_cell_ids)
    triangle_group_ids = np.array(triangle_group_ids)
    
    # N.B.: the triangle normals are inverted w.r.t. what MoD-ART expects. Flip them.
    triangles = triangles[:, ::-1]

    assert np.all(triangles < num_vertices), 'The triangle definitions include vertex indices out of range.'

    material_names = dict()
    for k, [mat_idx, n_dims] in mesh.field_data.items():
        if n_dims == 2:
            material_names[mat_idx] = k

    triangle_materials = list()
    for tri_id in range(num_triangles):
        # TODO: Consider the possibility of non-uniform materials within group; split group if that's the case.
        mat_id = mesh.cell_data['gmsh:physical'][triangle_cell_ids[tri_id]][0]
        triangle_materials.append(sanitize_ascii(material_names[mat_id]))
    
    obj_output_lines = list()
    mtl_output_lines = list()

    obj_output_lines.append('mtllib mesh.mtl\n')

    for v in vertices:
        line = 'v ' + ' '.join([str(c) for c in v]) + '\n'
        obj_output_lines.append(line)
    
    for i in range(num_triangles):
        patch_name = f'Patch_{triangle_group_ids[i]+1}_Mat_{triangle_materials[i]}'

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
            absorptions[sanitize_ascii(material)] = coeffs
    
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

        # Convert the .msh file into the format expected by MoD-ART.
        try:
            convert_mesh(result_container['msh_path'], temp_subfolder)
        except Exception as exc:
            raise RuntimeError('Failed to reformat the input mesh as required.') from exc

        # Save the material information into the .csv file expected by MoD-ART.
        try:
            save_materials_file(self.input_json_path)
        except Exception as exc:
            raise RuntimeError('Failed to reformat the material properties as required.') from exc

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

        # visualize_mesh(environment_folder)

        audio_sample_rate = result_container['fs_auralization']
        response_duration = result_container['simulationSettings']['durat']
        echogram_sample_rate = result_container['simulationSettings']['f_e']
        multiprocess_pool_size = result_container['simulationSettings']['pool']
        humidity = result_container['simulationSettings']['humi']
        temperature = result_container['simulationSettings']['temp']
        pressure = result_container['simulationSettings']['pres']
        points_per_square_meter = result_container['simulationSettings']['ppsm']
        rays_per_hemisphere = result_container['simulationSettings']['rays']
        T60_threshold = result_container['simulationSettings']['T60']
        max_slopes_per_band = result_container['simulationSettings']['slopes']
        
        # Run the pre-processing (shared by all sources, listeners).
        # TODO: Update progress bar.
        try:
            raves(environment_folder,
                  echogram_sample_rate=echogram_sample_rate,
                  multiprocess_pool_size=multiprocess_pool_size,
                  humidity=humidity, temperature=temperature, pressure=pressure,
                  points_per_square_meter=points_per_square_meter,
                  rays_per_hemisphere=rays_per_hemisphere,
                  T60_threshold=T60_threshold, max_slopes_per_band=max_slopes_per_band,
                  skip_T60_plots=True)
        except Exception as exc:
            raise RuntimeError('Failed to run the pre-processing environment analysis.') from exc

        for sim_idx, sim_dict in enumerate(result_container['results']):
            source_position = np.array([sim_dict['sourceX'],
                                        sim_dict['sourceY'],
                                        sim_dict['sourceZ']])
            listener_positions = np.array([[pos['x'], pos['y'], pos['z']]
                                           for pos in sim_dict['responses']])

            # Generate the echograms with MoD-ART.
            try:
                MoDART_tuple = run_MoDART(environment_folder,
                                          source_position, listener_positions,
                                          echogram_duration=response_duration,
                                          echogram_sample_rate=echogram_sample_rate,
                                          humidity=humidity, temperature=temperature, pressure=pressure,
                                          num_rays=rays_per_hemisphere)
                MoDART_echograms, frequencies, MoDART_data = MoDART_tuple
            except Exception as exc:
                raise RuntimeError(f'Failed to generate echograms for simulation #{sim_idx+1}.') from exc
            
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
            try:
                responses = noise_shaping(audio_sample_rate, len(audio_time_axis),
                                          frequencies, envelopes)
            except Exception as exc:
                raise RuntimeError(f'Failed to generate responses for simulation #{sim_idx+1}.') from exc

            # Write results back to JSON.
            for rec_idx in range(len(listener_positions)):
                # Note that the first index of "responses" is for the single source position.
                result_container['results'][sim_idx]['responses'][rec_idx]['receiverResults'] = responses[0, rec_idx].tolist()

        # Save the updated JSON
        with open(json_file_path, "w") as json_output:
            json_output.write(json.dumps(result_container, indent=4))

        print("MoDART simulation completed successfully!")
