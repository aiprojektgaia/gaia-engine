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

"""Input complexity limits for the comparison. Override with environment variables."""

import math
import os


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


# Comparison works on single tiles (typically ~1024 px square); 16 Mpx bounds
# the per-pixel label arrays and component statistics.
MAX_IMAGE_PIXELS = _env_int("GAIA_COMPARE_MAX_PIXELS", 16_000_000)
MAX_COMPONENTS = _env_int("GAIA_COMPARE_MAX_COMPONENTS", 20_000)
MAX_FEATURES = _env_int("GAIA_COMPARE_MAX_FEATURES", 20_000)
# Sum of all per-polygon crop areas in the removed-building pass.
MAX_RASTERIZED_PIXELS = _env_int("GAIA_COMPARE_MAX_RASTERIZED_PIXELS", 200_000_000)
# GeoJSON basemap structure, checked before geopandas/shapely see it.
MAX_BASEMAP_COORDINATES = _env_int("GAIA_COMPARE_MAX_COORDINATES", 2_000_000)
MAX_GEOMETRY_PARTS = _env_int("GAIA_COMPARE_MAX_GEOMETRY_PARTS", 100_000)
MAX_JSON_DEPTH = 12
# Realistic ground resolution range in meters per pixel.
MIN_RESOLUTION = 0.005
MAX_RESOLUTION = 100.0
MAX_KERNEL_SIZE = 2001


def check_image(image, name="image"):
    if image is None:
        raise ValueError(f"{name} could not be read")
    if image.size > MAX_IMAGE_PIXELS:
        raise ValueError(f"{name} has {image.size} pixels, the limit is {MAX_IMAGE_PIXELS}")


def check_resolution(resolution: float):
    if not math.isfinite(resolution) or not (MIN_RESOLUTION <= resolution <= MAX_RESOLUTION):
        raise ValueError(f"resolution {resolution} m/px is outside {MIN_RESOLUTION}..{MAX_RESOLUTION}")


def check_kernel(size: int) -> int:
    if size > MAX_KERNEL_SIZE:
        raise ValueError(f"morphology kernel {size} exceeds the limit {MAX_KERNEL_SIZE}")
    return size
