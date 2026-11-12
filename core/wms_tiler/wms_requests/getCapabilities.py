import requests
import xml.etree.ElementTree as ET

from models.LayerInfo import BoundingBox, LayerInfo


# this method will call the wms getCapabilities endpoint and return the capabilities
def get_capabilities(wms_server_url:str) -> list[LayerInfo]:
    # make a request to the wms getCapabilities endpoint, using the requests library
    add_wms = "" if wms_server_url.endswith('wms') else '/wms'
    xml = requests.get(f"{wms_server_url}{add_wms}?service=WMS&version=1.3.0&request=GetCapabilities")

    # parse the xml response
    root = ET.fromstring(xml.content)
    capability_child = root.find("Capability")
    layer_child = capability_child.find("Layer")
    layers = layer_child.findall("Layer")

    # and return the capabilities
    result = []
    for layer in layers:
        if layer.get("queryable") == "1":
            wgs84bbox_child = layer.find("LatLonBoundingBox")
            wgs84bbox = _get_bounding_box(wgs84bbox_child.get("minx"), wgs84bbox_child.get("miny"), wgs84bbox_child.get("maxx"), wgs84bbox_child.get("maxy"))
            bbox_child = layer.find("BoundingBox")
            bbox = _get_bounding_box(bbox_child.get("minx"), bbox_child.get("miny"), bbox_child.get("maxx"), bbox_child.get("maxy"))
            li = LayerInfo(
                name=layer.find("Name").text,
                title=layer.find("Title").text,
                srs=layer.find("SRS").text,
                wgs84_bounding_box=wgs84bbox,
                bounding_box=bbox,
            )

            result.append(li)

    return result

def _get_bounding_box(minx: str, miny: str, maxx: str, maxy: str) -> BoundingBox:
    return BoundingBox(float(minx), float(miny), float(maxx), float(maxy))