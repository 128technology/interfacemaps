# SSR Platform Interface Mappings

This contains a mapping of key interface information for Juniper SSR platforms. For each platform, the mapping includes details like PCI addresses, LTE device target interface names, best practice names and descriptions, and bezel images.

## Structure

### Device Maps JSON
The mapping data within this repo is primarily structured within the `devicemaps.json` file. The schema for this JSON is:

```
{
  "interfaceMap": {
    "Platform Manufacturer": {
      "Platform Model": {
        "ethernet": [],
        "lte": []
      }
    }
  }
}
```

The `ethernet` array contains objects ordered per ethernet port numbering visible on the bezel of the device. Each `ethernet` object provides the following data:

```
{
  "pciAddress": "0000:02:00.0",
  "type": "WAN",
  "name": "ge-0",
  "bcpNetwork": {
    "standaloneBranch": {
      "description": "Port 1 labeled on the device",
      "name": "wan-1"
    }
  }
}
```

`type` refers to a function of the interface when the device is provisioned using best current practice based templates, e.g. `LAN`, `WAN`, or `unused`.

The `bcpNetwork` object contains additional objects for names and descriptions of network-interfaces provisioned on the device interface, when best current practice based templates are used. These are keyed by a name for the BCP, e.g. `standaloneBranch`.

### Images

Each platform listed in `devicemaps.json` will have images within the `img` directory. Sub-directories follow the schema in `devicemaps.json`, e.g. `img`/`Platform Manufacturer`/`Platform Model`/.

Contained within each platform model subdirectory are images of the device. There will be a basic `bezel.png` showing the face and port layout of the device. Additionally there may be images showing diagrams corresponding to specific BCP designs. e.g. `standaloneBranch.jpg`.