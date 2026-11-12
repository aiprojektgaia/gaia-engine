import os
from pathlib import Path

from wms_requests.getMap import get_map
from models.LayerInfo import BoundingBox


def create_and_store_tile(wms_server_url: str, layer_name: str, output_path:str,
                          bbox: BoundingBox,
                          epsg: str, tile_size: int, image_format: str,
                          max_bytes: int) -> tuple[str, int]:
    """Download one tile straight to disk. Returns (path, bytes written).
    The body goes to a temporary '.part' file that is only renamed into place
    when complete, and removed on any failure."""
    # create tile name based on top_left bounds
    tile_name = (f"tile__{layer_name}_{bbox.min_x}_{bbox.max_y}.{image_format}"
                 .replace(":","__")
                 .replace("geotiff", "tif"))
    # store tile in storage
    # write file to output_path
    file_path = Path(output_path) / tile_name
    part_path = file_path.with_name(file_path.name + ".part")
    print(f"writing to {file_path}")
    try:
        with open(part_path, 'xb') as f:
            written = get_map(wms_server_url, layer_name, bbox, epsg, tile_size,
                              image_format, f, max_bytes)
        os.replace(part_path, file_path)
    except BaseException:
        try:
            os.remove(part_path)
        except OSError:
            pass
        raise

    # return tile path
    return str(file_path), written
