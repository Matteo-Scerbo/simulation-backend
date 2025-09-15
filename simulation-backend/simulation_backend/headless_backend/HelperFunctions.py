import os
import json


def find_input_file_in_subfolders(
    dirname=os.path.dirname(__file__), file_name="exampleInput.json"
):

    for subdir, dirs, files in os.walk(dirname):
        for file in files:
            filepath = os.path.join(subdir, file)

            if filepath.endswith(file_name):
                print(f"{file_name} has been found")
                return filepath

    raise FileNotFoundError(f"{file_name} has NOT been found")


def load_tmp_from_input(json_input_path):
    dirname = os.path.dirname(__file__)

    with open(json_input_path, "r") as json_input:
        data = json.load(json_input)

    # Make the relative geometry file paths absolute
    data["msh_path"] = find_input_file_in_subfolders(dirname, data["msh_path"])
    data["geo_path"] = find_input_file_in_subfolders(dirname, data["geo_path"])

    # Prepare the output file by copying the input into it. We need a separate output file to not overwrite the input file
    json_tmp_path = os.path.join(dirname, "MeasurementRoomTmp.json")
    with open(json_tmp_path, "w") as json_output:
        json_output.write(json.dumps(data, indent=4))

    return json_tmp_path


def save_results(json_tmp_path):
    def get_unique_filename(base_name="results", extension="json", subfolder="output"):
        """Generate a unique filename inside a subfolder relative to this script."""
        # Get the folder where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Make sure subfolder exists
        folder_path = os.path.join(script_dir, subfolder)
        os.makedirs(folder_path, exist_ok=True)

        # Start with results.json
        filename = os.path.join(folder_path, f"{base_name}.{extension}")
        counter = 1
        while os.path.exists(filename):
            filename = os.path.join(folder_path, f"{base_name} ({counter}).{extension}")
            counter += 1
        return filename

    file_name = get_unique_filename()

    with open(json_tmp_path, "r") as j:
        data = json.load(j)

    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print(f"Data written to {file_name}")
