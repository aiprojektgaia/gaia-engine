import requests

import limits

from models.LayerInfo import BoundingBox


def get_map(wms_server_url:str, layer_name: str, bbox: BoundingBox,
            epsg: str, tile_size: int, image_format: str, destination,
            max_bytes: int) -> int:
    """Fetch one tile and stream it into the open binary file `destination`.
    Returns the number of bytes written; never holds the body in memory."""
    add_wms = "" if wms_server_url.endswith('wms') else '/wms'
    limits.check_wms_url(wms_server_url)
    # query parameters are encoded by requests, never concatenated into the url
    url = f'{wms_server_url}{add_wms}'
    params = {
        'request': 'GetMap', 'service': 'WMS', 'version': '1.1.1',
        'layers': layer_name, 'styles': '', 'srs': epsg,
        'bbox': f'{bbox.min_x},{bbox.min_y},{bbox.max_x},{bbox.max_y}',
        'width': tile_size, 'height': tile_size, 'format': f'image/{image_format}',
    }
    #ble = "http://localhost:9600/geoserver/wms?request=GetMap&service=WMS&version=1.1.1&layers=gaia%3AGOT_6393_142&styles=&srs=EPSG%3A3007&bbox=142000.0,6393900.0,142100.0,6394000.0&width=1000 &height=1000&format=image%2Fgeotiff"

    try:
        print(f"calling {url}")
        # No redirects (a WMS must not bounce us to another host), bounded
        # timeouts, and a streamed body with a hard byte cap.
        with requests.get(url, params=params, stream=True, allow_redirects=False,
                          timeout=(limits.WMS_CONNECT_TIMEOUT, limits.WMS_READ_TIMEOUT)) as response:
            response.raise_for_status()
            declared = response.headers.get('Content-Length')
            if declared is not None and int(declared) > max_bytes:
                raise ValueError("WMS response exceeds the size limit")
            written = 0
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise ValueError("WMS response exceeds the size limit")
                destination.write(chunk)
            return written
    except (requests.exceptions.RequestException, ValueError) as e:
        # Raise a normal exception so the caller's failure callback runs;
        # SystemExit would skip every `except Exception`.
        print(f"[failed] Url called: {url}")
        print(f"Error: {e}")
        raise RuntimeError(f"WMS request failed: {e}") from e