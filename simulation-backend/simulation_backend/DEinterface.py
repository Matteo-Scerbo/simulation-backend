import json

import pickle
import time
import types
import pandas as pd

from math import ceil
from math import log

import gmsh



from Diffusion_Module.FiniteVolumeMethod.FunctionRT import t60_decay
from Diffusion_Module.FiniteVolumeMethod.FunctionClarity import *
from Diffusion_Module.FiniteVolumeMethod.FunctionDefinition import *
from Diffusion_Module.FiniteVolumeMethod.FunctionCentreTime import *
from Diffusion_Module.FiniteVolumeMethod.CreateMeshFVM import generate_mesh

from Diffusion_Module import *

import traceback

# Checking whether the 'should_cancel' flag has been set to True by the user
# Do not call this function all the time, as it is quite heavy
# This function should be called in the main calculation loop

def check_should_cancel(json_file_path_in):
    try:
        if json_file_path_in is not None:
            with open(json_file_path_in, 'r') as json_file_to_check:
                data = json.load(json_file_to_check)

        # Update the specified field value
        if 'should_cancel' in data:
            return data['should_cancel']

    except Exception as e:
        print("check_should_cancel returned: " + str(e))
        print(traceback.format_exc())

def de_method(json_file_path=None):

    st = time.time()  # start time of calculation
    result_container = {}
    if json_file_path is not None:
        with open(json_file_path, 'r') as json_file:
            result_container = json.load(json_file)

    if check_should_cancel(json_file_path):
        return
    
    # %%
    ###############################################################################
    # FIXED INPUTS
    ###############################################################################
    # General settings

    # Frequency range (could in the future retrieve from user input)
    fc_low = 125
    fc_high = 2000
    num_octave = 1

    x_frequencies = num_octave * log(fc_high / fc_low) / log(2)
    nBands = int(num_octave * log(fc_high / fc_low) / log(2) + 1)
    center_freq = fc_low * np.power(2, ((np.arange(0, x_frequencies + 1) / num_octave)))

    # Time discretization
    dt = 1 / 20000  # time discretization

    # Air absorption coefficient
    m_atm = 0  # air absorption coefficient [1/m]

    # Set initial condition - Source Info (interrupted method)
    Ws = 0.01  # Source point power [Watts] interrupted after "sourceon_time" seconds; 10^-2 W => correspondent to 100dB

    # Absorption term and Absorption coefficients
    th = 3  # int(input("Enter type Absortion conditions (option 1,2,3):"))
    # options Sabine (th=1), Eyring (th=2) and modified by Xiang (th=3)

    # Reference pressure in Pa
    pRef = 2 * (10 ** -5)  # Reference pressure in Pa

    # Air density
    rho = 1.21  # air density [kg.m^-3] at 20°C

    # Retrieve user input from results container
    use_default = True
    
    if result_container:
        simulation_settings = result_container["simulationSettings"]
        use_default = result_container["settingsPreset"] == "Default"

        if use_default:
            c0 = 343
        else:
            c0 = simulation_settings['de_c0']

        coord_source = [
            result_container["results"][0]['sourceX'],
            result_container["results"][0]['sourceY'],
            result_container["results"][0]['sourceZ'],
        ]

        coord_rec = [
            result_container["results"][0]['responses'][0]['x'],
            result_container["results"][0]['responses'][0]['y'],
            result_container["results"][0]['responses'][0]['z']
        ]
        geo_file_path = result_container['geo_path']
        msh_file_path = result_container['msh_path']
        generate_mesh (geo_file_path, msh_file_path, 1) # TODO: make this dependent on the room dimensions. We don't need an lc of 1 meter at all times..
    else:
        c0 = 343  # adiabatic speed of sound [m.s^-1]

    mesh = gmsh.open(msh_file_path)  # open the file

    ### Assign absorption coefficients to a material (group) and link it to the surfaces

    # Initialize a list to store surface tags and their absorption coefficients
    surface_absorption = [] #initialization absorption term (alpha*surfaceofwall) for each wall of the room
    triangle_face_absorption = [] #initialization absorption term for each triangle face at the boundary and per each wall
    absorption_coefficient_dict = {}

    # Loop over all groups (which are materials and can contain multiple surfaces (called entities in the surface_materials function))
    for group in vGroupsNames:
        if group[0] != 2:
            continue

        name_group = group[2]
        name_split = name_group.split("$")
        name_abs_coeff = name_split[0]

        if result_container:
            abscoeff = result_container['absorption_coefficients'][name_abs_coeff]
        else:
            abscoeff = input(
                f"Enter absorption coefficient for frequency {fc_low} to {fc_high} for {name_abs_coeff}:"
            )
        surface_materials (group, abscoeff, surface_absorption, absorption_coefficient_dict)


    for entity, Abs_term in surface_absorption:
        triangle_faces, _ = gmsh.model.mesh.getElementsByType(2, entity) #Get all the triangle faces for the current surface
        triangle_face_absorption.extend([Abs_term] * len(triangle_faces)) #Append the Abs_term value for each triangle face

    print("Correctly inputted surface materials. Starting initial geometry calculations...")

    #GMSH GET NODES, VOLUME ELEMENTS AND BOUNDARY ELEMENTS
    nodecoords, node_indices, bounEl, bounNode, voluEl, voluNode, belemNodes, velemNodes, boundaryEl_dict, volumeEl_dict = get_nodes_elem()

    #CALCULATION OF VOLUME CELLS AND CENTRE OF VOLUME
    cell_center, cell_volume = velem_volume_centre()

    #CALCULATION OF BOUNDARY ELEMENTS AND CENTRE OF AREA (might not need this function actually)
    barea_dict, centre_area = belem_area_centre()

    if check_should_cancel(json_file_path):
        return
    
    # CALCULATION OF NEIGHBOURS (might not need this function actually)
    fxt, txt, neighbourVolume = get_neighbour_faces()
    print("Completed initial geometry calculation. Starting internal tetrahedrons calculations...")

    # CALCULATION OF INTERIOR TETRAHEDRONS
    if check_should_cancel(json_file_path):
        return
    interior_tet, interior_tet_sum = interior_tetra()
    print("Completed internal tetrahedrons calculation. Starting boundary tetrahedrons calculations...")

    # CALCULATION OF ENTIRE SURFACE AREA PER MATERIAL
    surface_areas = surface_area(surface_absorption)

    if check_should_cancel(json_file_path):
        return
    
    # CALCULATION OF BOUNDARY ELEMENTS
    boundary_areas, total_boundArea = boundary_triang()
    print("Completed boundary tetrahedrons calculation. Starting main diffusion equation calculations over time and frequency...")

    # CALCULATION OF EQUIVALENT ABSORPTION AREA
    V, S, Eq_A = equiv_absorp(surface_areas)

    # CALCULATION OF SOURCE ON TIME
    sourceon_time = calculate_sourceon_time()

    # CALCULATION RECORDING TIME BASED ON THE SOURCE ON TIME
    if simulation_settings["sim_len_type"] == "edt":
        edt =  simulation_settings["edt"]
    else:
        edt = -1

    if simulation_settings["sim_len_type"] == "ir_length":
        ir_length = simulation_settings["de_ir_length"]
    else:
        ir_length = -1

    recording_time, t, recording_steps = rec_time(sourceon_time, dt, edt, ir_length)

    Dx, Dy, Dz = diff_coeff()

    dist_sr = dist_source_receiver()

    cl_tet_s_keys, total_weights_s = source_interp()

    Vs = source_volume()

    source1, sourceon_steps = initial_cond()

    s = source_matrix()

    cl_tet_r_keys, total_weights_r = receiver_interp()

    room_length, room_width, room_height = room_dimensions()

    x_axis, y_axis, line_rec_x_idx_list, dist_x, line_rec_y_idx_list, dist_y = line_receivers()

    beta_zero_freq = beta_zero()

    w_new_band, w_rec_band, w_rec_off_band, w_rec_off_deriv_band, p_rec_off_deriv_band, idx_w_rec, t_off = computing_energy_density()
    print("100% of main calculation completed")

    w_rec_x_band, w_rec_y_band, spl_stat_x_band, spl_stat_y_band, spl_r_band, spl_r_off_band, spl_r_norm_band, sch_db_band, t30_band, edt_band, c80_band, d50_band, ts_band = freq_parameters()

    et = time.time() #end time
    elapsed_time = et - st

    # To save all current variables
    save('results.pkl')

