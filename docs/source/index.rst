CHORAS simulation-backend
=========================

The CHORAS simulation-backend contains all interfaces to simulation methods and softwares connected to CHORAS.
Each simulation method is implemented as a separate package with a command line interface (CLI), which is used by
the CHORAS backend to run simulations. Simulation configurations are defined via JSON files, which are created 
by the CHORAS backend based on user input. After running a simulation, the results are passed back to the CHORAS backend
via the same JSON file used for configuration. 

.. toctree::
   :maxdepth: 1
   :caption: Contribution Guidelines

   includes/contributing.rst

.. toctree::
   :maxdepth: 1
   :caption: Examples

   auto_examples/index.rst

