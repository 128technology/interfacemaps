import click
import copy
import json
import pathlib


DEVICEMAP_PATH = pathlib.Path("./") / "devicemaps.json"

MODEL_TEMPLATE = {
    "model": "",
    "type": "gateway",
    "description": "",
    "t128_device": True,
    "has_oob": False,
    "_sub_required": "wan",
    "ha_node1_fpc": 1,
    "ports": {},
    "defaults": {},
}

@click.command()
@click.option(
    "-v",
    "--vendor",
    type=str,
    required=True
)
@click.option(
    "-s",
    "--skus",
    type=str,
    required=True
)
def run(vendor, skus):
    output = []
    for sku in skus.split(","):
        model = convert_sku(vendor, sku.strip())
        if model:
            output.append(model)
    
    print(json.dumps(output, indent=4))

def convert_sku(vendor, sku):
    sku_map = json.loads(pathlib.Path(DEVICEMAP_PATH).read_text())

    devicemap, _, actual_sku = lookup_devicemap(vendor, sku, sku_map)
    if not devicemap:
        return
    
    actual_devicemap = resolve_alias(devicemap, sku_map)

    model = copy.deepcopy(MODEL_TEMPLATE)
    model["model"] = actual_sku
    model["description"] = actual_devicemap.get("description")
    model.update(generate_ports(actual_devicemap))

    return model


def generate_ports(devicemap):
    has_oobm = False
    has_ha = False
    port_dict = {}
    wan = []
    lan = []
    for port in devicemap.get("ethernet"):
        p_type = port.get("type")
        if p_type == "SWITCH_PARENT":
            continue
        name = convert_port_name(port["name"], p_type=="MGMT")
        has_oobm = has_oobm or p_type == "MGMT"
        has_ha = has_ha or p_type == "HASync"
        if p_type == "WAN":
            wan.append(name)
        if p_type == "LAN":
            lan.append(name)
        
        p_dict = {"display": name}
        if port.get("pciAddress"):
            p_dict["pci_address"] = port.get("pciAddress")
        if port.get("speed"):
            p_dict["speed"] = port.get("speed")
        port_dict[name] = p_dict

    return {
        "ports": port_dict,
        "has_oob": has_oobm,
        "ha_node1_fpc": 1 if has_ha else 0,
        "defaults": {
            "wan_ports": ",".join(wan),
            # "lan_ports": ",".join(lan) commented until mist bug is fixed
            "lan_ports": lan[0]
        }
    }
        
        







def convert_port_name(name, is_mgmt=False):
    parts = name.split("-")
    identifier = parts.pop(0)
    if not is_mgmt:
        parts.insert(0, "0")
    location = "/".join(parts)

    return f"{identifier}-{location}"





def resolve_alias(devicemap, sku_map):
    if not devicemap.get("alias"):
        return devicemap
    child_map, _, _ = lookup_devicemap(
            devicemap["alias"]["vendor"],
            devicemap["alias"]["sku"],
            sku_map,
        )
    alias_map = resolve_alias(
        child_map,
        sku_map,
    )
    method = devicemap["alias"].get("method", "")

    del devicemap["alias"]

    if not alias_map.get("ethernet"):
        alias_map["ethernet"] = []
    if not alias_map.get("lte"):
        alias_map["lte"] = []

    if method.lower() == "append":
        try:
            alias_map["ethernet"].extend(devicemap.pop("ethernet"))
        except KeyError:
            pass
        try:
            alias_map["lte"].extend(devicemap.pop("lte"))
        except KeyError:
            pass

    alias_map.update(devicemap)
    return alias_map

def lookup_devicemap(vendor, sku, sku_map):
    actual_vendor = _lookup_longest_prefix_from_map(sku_map["interfaceMap"], vendor)
    if not actual_vendor:
        print(f"Vendor '{vendor}' not found")
        return None, None, None
    acutal_sku = _lookup_longest_prefix_from_map(
        sku_map["interfaceMap"][actual_vendor],
        sku,
    )
    if not acutal_sku:
        print(f"Sku '{sku}' for vendor '{vendor}' not found")
        return None, None, None
    return sku_map["interfaceMap"][actual_vendor][acutal_sku], actual_vendor, acutal_sku

def _lookup_longest_prefix_from_map(sku_map, target_key):
    target_key = target_key.lower()
    possible = [key for key in sku_map.keys() if target_key.startswith(key.lower())]
    possible.sort(reverse=True)
    return possible[0] if len(possible) > 0 else None

if __name__ == "__main__":
    run()