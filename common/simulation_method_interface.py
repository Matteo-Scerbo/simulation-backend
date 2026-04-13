from abc import ABC, abstractmethod
from pathlib import Path

class SimulationMethod(ABC):
    @abstractmethod
    def run_simulation(self, json_file_path: str | Path):
        """ Runs the simulation given a json file. """
        pass
    