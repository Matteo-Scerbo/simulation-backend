# This is the example interface file for connecting CHORAS to your method

# Import the relevant functions from 
from MyNewMethod.My_New_Method import simulation_method

# This function will be called from app/services/simulation_service.py
def mynewmethod_method (json_file_path=None):

    print("mynewmethod_method: starting simulation")

    # Call the appropriate function in your package
    simulation_method (json_file_path)

    print("mynewmethod_method: simulation done!")

