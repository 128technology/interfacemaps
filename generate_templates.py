import pathlib
import json
import copy
import sys

DEVICEMAP_PATH = pathlib.Path("./") / "devicemaps.json"
TEMPLATE_DIR = pathlib.Path("./templates")
IMG_DIR = pathlib.Path("./img")
LTE_HELP_TIP = "LTE is available on your platform."
BEZEL_TIP = "Below are the ports that will be assigned.\n\n### {vendor} {model}\n\n![{vendor} {model}](https://raw.githubusercontent.com/128technology/interfacemaps/master/img/{vendor}/{model}/standaloneBranch.jpg)\n\n"
HELP_TEMPLATE = "# {vendor} {model} Router\n\nThis adds a basic {vendor} {model} Session Smart Router to your configuration.\n{LTE_TIP}\n\n\n\n##Generate Config\nSelect the generate config icon at the top of the page, and proceed to configuration. Validate and commit to finish adding the new router to running configuration.\n\n## Port Details\nThis template assumes all WAN interfaces on your device will be connected to a network providing it DHCP address assignment, and with connectivity to your conductor.\n\nIt will configure LAN interfaces providing a DHCP server to connected endpoints. From the LAN, the router local GUI and CLI will be accessible at `192.168.128.1`\n\n{bezel_tip}"
BASE_BODY = {
    "authority": {
        "security": [
            {
                "name": "internal-encrypt-hmac-disable",
                "description": "Security policy built by builtin router template",
                "encrypt": "false",
                "adaptiveEncryption": "false",
                "hmacMode": "disabled"
            }
        ],
        "router": [
            {
                "_value": {
                    "name": "{{routerName}}",
                    "description": "{{routerDescription}}",
                    "location": "{{routerLocation}}",
                    "interNodeSecurity": "internal-encrypt-hmac-disable",
                    "system": {
                        "ntp": {
                            "server": [
                                {
                                    "ipAddress": "216.239.35.0"
                                },
                                {
                                    "ipAddress": "216.239.35.4"
                                },
                                {
                                    "ipAddress": "216.239.35.8"
                                },
                                {
                                    "ipAddress": "216.239.35.12"
                                }
                            ]
                        }
                    },
                    "dnsConfig": [
                        {
                            "mode": "static",
                            "address": [
                                "1.1.1.1",
                                "8.8.8.8"
                            ]
                        }
                    ],
                    "applicationIdentification": {
                        "mode": [
                            "all"
                        ]
                    },
                    "node": [
                        {
                            "name": "node1",
                            "role": "combo",
                            "description": "{{routerName}} router node",
                        }
                    ]
                },
                "_operation": "create"
            }
        ]
    }
}
BASE_SCHEMA = {
    "type": "object",
    "definitions": {
        "wanPort": {
            "type": "object",
            "properties": {
                "conductor": {
                    "title": "Conductor can be reached from this interface",
                    "type": "boolean",
                    "default": True,
                    "readOnly": True
                },
                "dhcpClient": {
                    "title": "Address learned using DHCP",
                    "type": "boolean",
                    "default": True,
                    "readOnly": True
                }
            },
            "dependencies": {
                "dhcpClient": {
                    "oneOf": [
                        {
                            "properties": {
                                "dhcpClient": {
                                    "const": True,
                                    "readOnly": True
                                }
                            }
                        },
                        {
                            "properties": {
                                "dhcpClient": {
                                    "const": False,
                                    "readOnly": True
                                },
                                "address": {
                                    "title": "IP address",
                                    "type": "string",
                                    "description": "Network interface IP address. Example: 128.128.128.2",
                                    "readOnly": True
                                },
                                "prefix": {
                                    "title": "Prefix",
                                    "type": "string",
                                    "description": "Network prefix length. Example: 24",
                                    "readOnly": True
                                },
                                "gateway": {
                                    "title": "Gateway",
                                    "type": "string",
                                    "description": "Network gateway IP address. Example: 128.128.128.1",
                                    "readOnly": True
                                }
                            }
                        }
                    ]
                },
                "dhcpServer": {
                    "oneOf": [
                        {
                            "properties": {
                                "dhcpServer": {
                                    "const": True,
                                    "readOnly": True
                                },
                                "dhcpServerStartAddr": {
                                    "title": "DHCP server pool start address",
                                    "type": "string",
                                    "default": "192.168.128.100",
                                    "readOnly": True
                                },
                                "dhcpServerEndAddr": {
                                    "title": "DHCP server pool end address",
                                    "type": "string",
                                    "default": "192.168.128.254",
                                    "readOnly": True
                                }
                            }
                        },
                        {
                            "properties": {
                                "dhcpServer": {
                                    "const": False,
                                    "readOnly": True
                                }
                            }
                        }
                    ]
                }
            }
        },
        "lanPort": {
            "type": "object",
            "properties": {
                "web": {
                    "title": "Management GUI",
                    "description": "Enable web access to the node management GUI using HTTPS.",
                    "type": "boolean",
                    "default": True,
                    "readOnly": True
                },
                "ssh": {
                    "title": "Management SSH",
                    "description": "Enable terminal access to the node management CLI using SSH.",
                    "type": "boolean",
                    "default": True,
                    "readOnly": True
                },
                "dhcpServer": {
                    "title": "DHCP Server",
                    "description": "Enable DHCP server on the interface.",
                    "type": "boolean",
                    "default": True,
                    "readOnly": True
                }
            }
        },
        "ltePort": {
            "type": "object",
            "properties": {
            }
        },
        "mgmtPort": {
            "type": "object",
            "properties": {
            }
        }
    }
}


def main():
    interfacemap = json.loads(DEVICEMAP_PATH.read_text())

    for vendor, skus in interfacemap["interfaceMap"].items():
        models = set()
        for sku, devicemap in skus.items():
            actual_devicemap = resolve_alias(devicemap, interfacemap)
            if not actual_devicemap:
                continue

            model = devicemap.get("displayModel", sku)

            # make sure models are unique per vendor
            if model in models:
                print(f"Vendor {vendor} has duplicate model {model}")
                sys.exit(1)

            models.add(model)

            template = generate_template(vendor, model, actual_devicemap)
            write_template(vendor, model, template)

def generate_template(vendor, model, devicemap):
    description_suffix = ""
    if devicemap.get('description'):
        description_suffix = f": {devicemap.get('description')}"

    return {
        "name": f"{vendor}-{model}-Template",
        "description": f"Adds a standalone {vendor} {model} router{description_suffix}",
        "enabled": True,
        "persistInput": False,
        "builtin": True,
        "mode": "advanced",
        "help": format_help_msg(vendor, model, bool(devicemap.get("lte"))),
        "body": f"{{% editgroup %}}\n\n{json.dumps(generate_body(devicemap), indent=2)}",
        "schema": generate_schema(vendor, model, devicemap)
    }


def generate_body(devicemap):
    device_interfaces = []
    for index, lte_interface in enumerate(devicemap.get("lte", [])):
        device_interfaces.append(
            {
                "name": lte_interface["name"],
                "description": lte_interface["description"],
                "type": "lte",
                "enabled": "true",
                "forwarding": "true",
                "targetInterface": lte_interface["targetInterface"],
                "networkInterface": [
                    {
                        "name": lte_interface["name"],
                        "description": lte_interface.get("bcpNetwork", {}).get("standaloneBranch", {}).get("description", ""),
                        "sourceNat": "true",
                        "management": "false",
                        "defaultRoute": "false",
                        "managementVector": {
                            "priority": f"20{index}",
                            "name": "mgmt"
                        },
                        "dhcp": "v4"
                    }
                ]
            }
        )
    def_route_exists = False
    for index, dev_intf in enumerate(devicemap["ethernet"]):
        if dev_intf["type"] == "MGMT":
            continue
        intf = {"pciAddress": dev_intf["pciAddress"]} if dev_intf.get("pciAddress") else {}
        intf = {
            "description": dev_intf["description"],
            "enabled": "true",
            "forwarding": "true",
            "name": dev_intf["name"]
        }
        if dev_intf["type"] == "WAN":
            intf["networkInterface"] = [
                {
                    "name": dev_intf.get("bcpNetwork", {}).get("standaloneBranch", {}).get("name", f"{dev_intf['name']} Network Interface"),
                    "description": dev_intf.get("bcpNetwork", {}).get("standaloneBranch", {}).get("description", ""),
                    "sourceNat": "true",
                    "dhcp": "v4",
                    "conductor": "true",
                    "management": "true",
                    "defaultRoute": "true" if not def_route_exists else False,
                    "managementVector": {
                        "priority": f"10{index}",
                        "name": "mgmt"
                    }
                }
            ]
            def_route_exists = True
        else:
            intf["networkInterface"] = [
                {
                    "name": dev_intf.get("bcpNetwork", {}).get("standaloneBranch", {}).get("name", f"{dev_intf['name']} Network Interface"),
                    "description": dev_intf.get("bcpNetwork", {}).get("standaloneBranch", {}).get("description", ""),
                    "address": [
                        {
                            "prefixLength": "24",
                            "ipAddress": "192.168.128.1",
                            "hostService": [
                                {
                                    "serviceType": "ssh",
                                    "description": "SSH management",
                                    "enabled": "true"
                                },
                                {
                                    "serviceType": "dhcp-server",
                                    "serverName": "{{ routerName }}",
                                    "addressPool": [
                                        {
                                            "startAddress": "192.168.128.100",
                                            "endAddress": "192.168.128.200",
                                            "router": [
                                                "192.168.128.1"
                                            ],
                                            "domainServer": [
                                                "1.1.1.1",
                                                "8.8.8.8"
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "serviceType": "web",
                                    "description": "Web GUI Management",
                                    "enabled": "true"
                                }
                            ]
                        }
                    ]
                }
            ]
        device_interfaces.append(intf)

    body = copy.deepcopy(BASE_BODY)

    body["authority"]["router"][0]["_value"]["node"][0]["deviceInterface"] = device_interfaces

    return body


def format_help_msg(vendor, model, is_lte):
    bezel_tip = BEZEL_TIP.format(
        vendor=vendor, model=model) if img_exists(vendor, model) else ""
    return HELP_TEMPLATE.format(
        vendor=vendor,
        model=model,
        LTE_TIP=LTE_HELP_TIP if is_lte else "",
        bezel_tip=bezel_tip
    )

def generate_schema(vendor, model, devicemap):
    schema = copy.deepcopy(BASE_SCHEMA)

    schema["title"] = f"New {vendor} {model} branch router"
    schema["description"] = f"Add a new {vendor} {model} branch router to the configuration."
    props = {
        "routerName": {
            "title": "Router Name",
            "description": "Enter a name identifier for the router.",
            "type": "string"
        },
        "routerDescription": {
            "title": "Description",
            "description": "Description for the router.",
            "type": "string"
        },
        "routerLocation": {
            "title": "Site Location",
            "description": "Enter the address or location of the router. Example: City, State.",
            "type": "string"
        }
    }

    props["ports"] = {
        "type": "object",
        "title": "Ports",
        "description": "Port and network settings.",
        "properties": generate_port_schema(devicemap)
    }
    schema["properties"] = props
    return schema


def generate_port_schema(devicemap):
    properties = {}
    for port in devicemap["ethernet"] + devicemap.get("lte", []):
        if port["type"] in ["MGMT", "WAN", "LTE"]:
            simplified_type = port["type"]
        else:
            simplified_type = "LAN"

        properties[port["name"]] = {
            "title": f"{simplified_type} - {port['name']}",
            "description": port["description"],
            "$ref": f"#/definitions/{simplified_type.lower()}Port"
        }
    return properties


def write_template(vendor, model, template):
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    template_path = TEMPLATE_DIR / f"{vendor}-{model}-template.json"

    template_path.write_text(json.dumps(template, indent=2))


def img_exists(vendor, model):
    img_path = IMG_DIR / vendor / model / "standaloneBranch.jpg"
    return img_path.exists()

def resolve_alias(devicemap, sku_map):
    if not devicemap.get("alias"):
        return devicemap
    if not (devicemap.get("ethernet") or devicemap.get("lte")):
        return None
    alias_map = resolve_alias(
        lookup_devicemap(
            devicemap["alias"]["vendor"],
            devicemap["alias"]["sku"],
            sku_map,
        ),
        sku_map,
    )
    del devicemap["alias"]
    alias_map.update(devicemap)
    return alias_map

def lookup_devicemap(vendor, sku, sku_map):
    actual_vendor = _lookup_longest_prefix_from_map(sku_map["interfaceMap"], vendor)
    acutal_sku = _lookup_longest_prefix_from_map(
        sku_map["interfaceMap"][actual_vendor],
        sku,
    )
    return sku_map["interfaceMap"][actual_vendor][acutal_sku]

def _lookup_longest_prefix_from_map(sku_map, target_key):
    target_key = target_key.lower()
    possible = [key for key in sku_map.keys() if target_key.startswith(key.lower())]
    possible.sort(reverse=True)
    return possible[0] if len(possible) > 0 else None

if __name__ == "__main__":
    main()
