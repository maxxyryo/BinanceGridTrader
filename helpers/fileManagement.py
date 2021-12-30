import os
import sys
import json

project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)


class FileManager():
    def __init__(self):
        pass

    def read_json_file(self, file_name: str):
        """
        Read file
        :return: Block height as INT
        """
        path = f'{project_path}/{file_name}'
        try:
            with open(path) as json_file:
                data = json.load(json_file)
                return data
        except IOError:
            return None
        except json.decoder.JSONDecodeError:
            return None

    def update_json_file(self, file_name: str, values: dict):
        try:
            # read data
            # data = read_json_file(file_name)
            path = f'{project_path}/{file_name}'
            with open(path, 'w') as f:
                json.dump(values, f)
            return True
        except Exception:
            return False
