import json
from typing import Callable, Tuple


def use_json_file(path) -> Tuple[Callable[[], dict], Callable[[dict], dict]]:
    def read():
        with open(path, "r") as f:
            return json.loads(f.read())

    def write(data):
        with open(path, "w") as f:
            f.write(json.dumps(data))
        return data

    return read, write
