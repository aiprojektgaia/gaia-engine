# Copyright 2023-2026 The GAIA project contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Resource limits for the WMS tiler. Override with environment variables."""

import math
import os
import re
from urllib.parse import urlsplit


def _env_number(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


MAX_TILES = int(_env_number("GAIA_TILER_MAX_TILES", 10_000))
MAX_TILE_PIXELS = int(_env_number("GAIA_TILER_MAX_TILE_PIXELS", 8192))
MAX_OVERLAP_PERCENT = 50
WMS_CONNECT_TIMEOUT = _env_number("GAIA_WMS_CONNECT_TIMEOUT", 10)
WMS_READ_TIMEOUT = _env_number("GAIA_WMS_READ_TIMEOUT", 120)
WMS_MAX_RESPONSE_BYTES = int(_env_number("GAIA_WMS_MAX_RESPONSE_BYTES", 512 * 1024 * 1024))
WMS_TOTAL_DEADLINE_SECONDS = _env_number("GAIA_TILER_DEADLINE_SECONDS", 4 * 3600)
# Job-wide budgets: total pixels requested (tiles x width x height) and total
# bytes written. ~4e9 px is about 3,800 tiles of 1024 px (~25 km2 at 0.08 m/px).
MAX_JOB_PIXELS = int(_env_number("GAIA_TILER_MAX_JOB_PIXELS", 4_000_000_000))
MAX_JOB_BYTES = int(_env_number("GAIA_TILER_MAX_JOB_BYTES", 20 * 1024**3))


def max_tile_response_bytes(tile_size_pixels: int) -> int:
    """Per-tile response cap: an uncompressed 4-band 16-bit tile plus headroom,
    and never more than WMS_MAX_RESPONSE_BYTES."""
    return min(WMS_MAX_RESPONSE_BYTES, tile_size_pixels * tile_size_pixels * 8 + 1024 * 1024)


# Origins the tiler may call. The default is the GeoServer shipped with GAIA;
# set GAIA_WMS_ALLOWED_ORIGINS (comma separated, e.g. "http://geoserver:8080")
# for other deployments. Redirects are never followed.
ALLOWED_WMS_ORIGINS = {
    o.strip().rstrip("/").lower()
    for o in os.environ.get(
        "GAIA_WMS_ALLOWED_ORIGINS", "http://localhost:9600,http://127.0.0.1:9600"
    ).split(",")
    if o.strip()
}
ALLOWED_IMAGE_FORMATS = {"geotiff", "tiff", "tif", "png", "jpeg"}
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_:.\-]{0,127}$")


def check_wms_url(url: str) -> None:
    """Allow only configured WMS origins (scheme, host and port must match)."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("WMS url must be an http(s) url without credentials")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    host = parts.hostname.lower()
    host = f"[{host}]" if ":" in host else host
    origin = f"{parts.scheme}://{host}:{port}"
    allowed = set()
    for o in ALLOWED_WMS_ORIGINS:
        p = urlsplit(o)
        h = (p.hostname or "").lower()
        h = f"[{h}]" if ":" in h else h
        allowed.add(f"{p.scheme}://{h}:{p.port or (443 if p.scheme == 'https' else 80)}")
    if origin not in allowed:
        raise ValueError(f"WMS origin {origin} is not in GAIA_WMS_ALLOWED_ORIGINS")


def check_names(layer_name: str, epsg: str, image_format: str) -> None:
    """layer_name and image_format end up in file names and in the WMS query."""
    if not _SAFE_NAME.match(layer_name) or ".." in layer_name:
        raise ValueError("invalid layer name")
    if not re.match(r"^EPSG:\d{3,6}$", epsg):
        raise ValueError("epsg must look like EPSG:3006")
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValueError(f"image format must be one of {sorted(ALLOWED_IMAGE_FORMATS)}")


def validate_tiling_parameters(min_x, min_y, max_x, max_y, mpp, tile_size_pixels, overlap) -> int:
    """Validate untrusted tiling input and return the number of tiles it will produce.

    Raises ValueError for anything non-finite, unordered, non-positive or over quota.
    """
    for name, value in (("bbox", (min_x, min_y, max_x, max_y)), ("mpp", (mpp,))):
        if not all(math.isfinite(v) for v in value):
            raise ValueError(f"{name} must be finite")
    if not (min_x < max_x and min_y < max_y):
        raise ValueError("bbox must have min < max in both axes")
    if mpp <= 0:
        raise ValueError("mpp must be positive")
    if not (0 < tile_size_pixels <= MAX_TILE_PIXELS):
        raise ValueError(f"tile size must be between 1 and {MAX_TILE_PIXELS} pixels")
    if not (0 <= overlap <= MAX_OVERLAP_PERCENT):
        raise ValueError(f"overlap must be between 0 and {MAX_OVERLAP_PERCENT} percent")

    step = mpp * tile_size_pixels * 100 / (overlap + 100)
    if not math.isfinite(step) or step <= 0:
        raise ValueError("tile size in meters is not usable")
    columns = math.ceil((max_x - min_x) / step)
    rows = math.ceil((max_y - min_y) / step)
    if columns * rows > MAX_TILES:
        raise ValueError(f"{columns * rows} tiles requested, the limit is {MAX_TILES}")
    job_pixels = columns * rows * tile_size_pixels * tile_size_pixels
    if job_pixels > MAX_JOB_PIXELS:
        raise ValueError(f"{job_pixels} pixels requested, the limit is {MAX_JOB_PIXELS}")
    return columns * rows
