"""Module implementing a CHORAS interface for MoDART.
"""
import json
import numpy as np
from pathlib import Path

from pprint import pprint
from raves import raves, run_MoDART
from raves.src.utils import visualize_mesh

from numpy.random import default_rng
from scipy.signal import butter, sosfilt
from scipy.interpolate import make_interp_spline

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

        # N.B.: the triangle normals are inverted w.r.t. what MoD-ART expects. Flip them.
        triangles = triangles[:, ::-1]

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
        print('\tDEBUG MESSAGE: writing temp files:')
        print('\t\t', obj_path)
        print('\t\t', mtl_path)
        
        with open(obj_path, mode='w') as file:
            for line in obj_output_lines:
                file.write(line)
        with open(mtl_path, mode='w') as file:
            for line in mtl_output_lines:
                file.write(line)
        
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
        
        csv_path = str(temp_subfolder / 'materials.csv')
        print('\tDEBUG MESSAGE: writing temp file:')
        print('\t\t', csv_path)

        with open(csv_path, mode='w') as file:
            line = 'Frequencies, ' + ', '.join([str(f) for f in freq_bands]) + '\n'
            file.write(line)

            for material, coeffs in absorptions.items():
                line = material + ', ' + ', '.join([str(c) for c in coeffs]) + '\n'
                file.write(line)

                # TODO: For now, scattering coefficients are arbitrarily set to 0.3.
                #       Eventually they will be sent by the backend.
                line = material + ', 0.3\n'
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

        print('\tDEBUG MESSAGE: JSON contents:')
        pprint(result_container)
        print()

        environment_folder = result_container['MoDART_data_subfolder']

        # visualize_mesh(environment_folder)
        
        print('\tDEBUG MESSAGE: precomputation\n')

        raves(environment_folder)

        print('\tDEBUG MESSAGE: runtime computation')

        for sim_idx, sim_dict in enumerate(result_container['results']):
            source_position = np.array([
                sim_dict['sourceX'],
                sim_dict['sourceY'],
                sim_dict['sourceZ'],
            ])
            listener_positions = np.array([[pos['x'], pos['y'], pos['z']]
                                           for pos in sim_dict['responses']])

            # TODO: echogram_sample_rate will eventually be a parameter set by the user.
            echogram_sample_rate = int(1e3)
            # TODO: audio_sample_rate will eventually be a parameter set by...?
            audio_sample_rate = int(44.1e3)
            # TODO: this will eventually be named something else in the JSON.
            response_duration = result_container['simulationSettings']['de_ir_length']

            print('\t\tgenerating echograms')

            # Generate the echograms with MoD-ART.
            MoDART_echograms, frequencies, _ = run_MoDART(environment_folder,
                                                          source_position, listener_positions,
                                                          echogram_duration=response_duration,
                                                          echogram_sample_rate=echogram_sample_rate)
            
            print('\t\techogram shape:', MoDART_echograms.shape)
            
            print('\t\tupsampling echograms')

            # Take note of the echogram energy, to compare it after upsampling.
            old_energy = np.sum(MoDART_echograms, axis=-1)
            
            # Prepare the audio-rate time intervals at which we'll evaluate the upsampled echogram.
            echogram_time_axis = np.arange(0, response_duration, 1 / echogram_sample_rate)
            audio_time_axis = np.arange(0, response_duration, 1 / audio_sample_rate)
            # We use a linear interpolation, because any other upsampling algorithm risks introducing negative values.
            linear_spline = make_interp_spline(echogram_time_axis, MoDART_echograms, k=1, axis=-1)
            upsampled_echograms = linear_spline(audio_time_axis)
            
            # Normalize w.r.t. the new sample rate, to preserve the energy-per-second definition of echogram values.
            upsampled_echograms *= echogram_sample_rate / audio_sample_rate
            
            # Compare the new energy to the old one.
            new_energy = np.sum(upsampled_echograms, axis=-1)
            # The ratio (averaged over all frequency bands) should be close to 1 for all sources and listeners.
            print('\t\techogram energy normalization:', old_energy / new_energy)

            print('\t\tamplitude modulation of noise signal')

            # Random number generator for the stochastic signal to be modulated.
            rng = default_rng()
            
            # White noise
            #   noise_signal = rng.normal(size=len(audio_time_axis))
            # Poisson process
            noise_signal = rng.poisson(lam=0.5, size=len(audio_time_axis)).astype(float)

            # Ensure the noise signal has unit energy per second, matching the
            #   convention used to generate the echograms.
            noise_signal *= np.sqrt(response_duration / np.sum(noise_signal**2))
            
            # Factor for octave-band boundaries.
            # TODO: These may become third-octave bands at some point.
            band_bound = np.sqrt(2)
            # Consider the frequency band centers provided alongside the input data.
            band_centers = frequencies
            num_bands = len(frequencies)
            
            # Ensure that all frequencies support band-pass filtering.
            if np.any(band_centers * band_bound >= audio_sample_rate):
                print('Warning: the audio sample rate is too low for some frequency bands.')
                # Select only acceptable bands.
                band_centers = band_centers[band_centers * band_bound < audio_sample_rate]
                # Update the number of rendered bands.
                num_bands = len(band_centers)
                # Drop unused bands from the echogram, to preserve the right shape.
                upsampled_echograms = upsampled_echograms[:, :, :num_bands]
            
            # Prepare an array for the band-pass filtered signals.
            filtered_noise_signals = np.zeros((num_bands, len(audio_time_axis)))
            
            print('\t\tfiltered_noise_signals shape:', filtered_noise_signals.shape)
            
            for b in range(num_bands):
                # Prepare the suitable band-pass filter...
                sos = butter(6, (band_centers[b] / band_bound,
                                band_centers[b] * band_bound),
                            btype='bandpass', output='sos',
                            fs=audio_sample_rate)
                # ...and apply it to the stochastic signal.
                filtered_noise_signals[b] = sosfilt(sos, noise_signal)
            
            # Translate the energy envelopes to amplitude envelopes.
            envelopes = np.sqrt(upsampled_echograms)
            
            # The envelope array has shape (S, L, B, T), the noise signals have shape (B, T):
            #   we need to add two "leading" dimensions, which is done using [None, None].
            modulated_noise_signals = envelopes * filtered_noise_signals[None, None]
            
            print('\t\tmodulated_noise_signals shape:', modulated_noise_signals.shape)
            
            # The dimension of index 2 holds the separate frequency bands.
            # Sum the array along that dimension to obtain the complete room impulse responses.
            responses = np.sum(modulated_noise_signals, axis=2)

            print('\t\tresponses shape:', responses.shape)
            
            # Write results back to JSON.
            for rec_idx in range(len(listener_positions)):
                # Note that the first index of "responses" is for the single source position.
                result_container['results'][sim_idx]['responses'][rec_idx]['receiverResults'] = responses[0, rec_idx].tolist()

        print('\tDEBUG MESSAGE: ending _modart_method\n')

        # Save the updated JSON
        with open(json_file_path, "w") as json_output:
            json_output.write(json.dumps(result_container, indent=4))

        print("MoDART simulation completed successfully!")
