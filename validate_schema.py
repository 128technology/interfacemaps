import jsonschema
import json
import pathlib

import pkg_resources

DIRECTORY = pathlib.Path(pkg_resources.resource_filename(__name__, ""))

DEVICE_MAP_SCHEMA_PATH = DIRECTORY / "devicemap-schema.json"
SKU_MAP_SCHEMA_PATH = DIRECTORY / "skumap-schema.json"
DEVICE_MAP_PATH = DIRECTORY / "devicemaps.json"

DEVICE_MAP_SCHEMA = json.loads(DEVICE_MAP_SCHEMA_PATH.read_text())
SKU_MAP_SCHEMA = json.loads(SKU_MAP_SCHEMA_PATH.read_text())

DEVICE_MAP = json.loads(DEVICE_MAP_PATH.read_text())

def main():
    resolver = jsonschema.RefResolver(
        referrer=SKU_MAP_SCHEMA, base_uri=f"file://{DIRECTORY}/"
    )
    jsonschema.validate(DEVICE_MAP, SKU_MAP_SCHEMA, resolver=resolver)


if __name__ == "__main__":
    main()
