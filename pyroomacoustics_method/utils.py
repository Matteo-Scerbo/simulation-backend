"""Utility functions for pyroomacoustics method."""
from abc import ABC, abstractmethod
from pathlib import Path
import time

import requests


class SimulationMethod(ABC):
    @abstractmethod
    def run_simulation(self, json_file_path: str | Path):
        """Run the simulation given a JSON file."""
        pass


def save_results(
    json_tmp_file,
    url="http://host.docker.internal:5001/receive",
    max_retries=5,
    delay=2,
):
    """Save simulation results to the results server."""
    for attempt in range(1, max_retries + 1):
        try:
            with open(json_tmp_file, "rb") as f:
                response = requests.post(url, files={"file": f})

            if response.status_code == 200:
                print("Successfully sent file.")
                return True

            print(f"Attempt {attempt}: Server returned {response.status_code}")
        except requests.RequestException as exc:
            print(f"Attempt {attempt}: Request failed - {exc}")

        time.sleep(delay)

    print("Max retries reached. Giving up.")
    return False
