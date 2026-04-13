# ⚠️ The simulation methods provided here are incomplete.

## Context
- Folders: `deeponet_method/`, `pyroomacoustics_method/`
---

## Problems
Although this repository also contains implementations for simulation methods based on DeepONet and Pyroomacoustics, these specific implementations originated from an older version of CHORAS, and are not yet functional. 

### Pyroomacoustics
The Pyroomacoustics method does not work as it expects a slightly different JSON file structure than what is created by the backend in the `uploads/` directory when a new simulation is started. Refer to `common/exampleInput_DE.json` or `common/exampleInput_DG.json` for guidance on what structure the backend currently generates. `common/exampleInput_pyroomacoustics.json` has been kept for reference, this file reflects the input structure expected by the currently incompatible Pyroomacoustics implementation.

### Solution
The functions in `pyroomacoustics_method/PyroomacousticsInterface.py` should be modified to work with the JSON created by the backend in the `uploads/` directory.

### DeepONet
The DeepONet method is incompatible with the current backend, as it does not conform to the functionality which the backend expects. To help standardize simulation method implementations, we recommend that all methods implement the `SimulationMethod` interface (see `dg_method/DGinterface.py` for an example of how to do this). The `run_simulation()` method of the interface should only accept the path to the simulation's JSON file within the `uploads/` directory in the main CHORAS folder, and write results to the same JSON directly. The DeepONet implementation does not currently do this. 

Similarly, note that the `__main__` function in `deeponet_method/DeepONetInterface.py` is currently not being used to run containerized simulation logic given a particular input JSON (which is the intended use), rather it loads the template `exampleInput_deeponet_acoustics.json` and tests that the simulation function runs. 

### Solution
The functions in `deeponet_method/DeepONetInterface.py` should be modified to only read from and write to a simulation's JSON file within the `uploads/` directory. The `__main__` function in `deeponet_method/DeepONetInterface.py` should be modified to run simulation logic given a particular simulation's JSON (see e.g. `dg_method/DGinterface.py` for an example). 


