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

"""Input budgets for vectorisation. Override with environment variables.

The mask's georeference and content come from earlier pipeline stages and are
treated as untrusted: they decide filter sizes, contour counts and geometry
work, so all of those are bounded before the expensive call is made.
"""

import math
import os


def _env(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


MIN_PIXEL_SIZE = _env("GAIA_VECTORIZE_MIN_PIXEL_SIZE", 0.005)   # m/px
MAX_PIXEL_SIZE = _env("GAIA_VECTORIZE_MAX_PIXEL_SIZE", 100.0)
MAX_FILTER_RADIUS_PX = int(_env("GAIA_VECTORIZE_MAX_FILTER_RADIUS", 200))
MAX_CONTOURS = int(_env("GAIA_VECTORIZE_MAX_CONTOURS", 200_000))
MAX_VERTICES = int(_env("GAIA_VECTORIZE_MAX_VERTICES", 20_000_000))
# Building masks are clipped per contour; bound the summed crop area.
MAX_CROP_PIXELS = int(_env("GAIA_VECTORIZE_MAX_CROP_PIXELS", 2_000_000_000))


def pixel_size_from_transform(transform) -> float:
    """Validate the affine transform and return the (square) pixel size in m."""
    a, b, d, e = transform.a, transform.b, transform.d, transform.e
    if not all(math.isfinite(v) for v in (a, b, d, e, transform.c, transform.f)):
        raise ValueError("raster transform must be finite")
    if b != 0 or d != 0:
        raise ValueError("rotated or sheared rasters are not supported")
    size_x, size_y = abs(a), abs(e)
    if not (MIN_PIXEL_SIZE <= size_x <= MAX_PIXEL_SIZE):
        raise ValueError(f"pixel size {size_x} m is outside {MIN_PIXEL_SIZE}..{MAX_PIXEL_SIZE}")
    if abs(size_x - size_y) > 0.01 * size_x:
        raise ValueError("pixels must be square")
    return size_x


def check_filter_radius(value_m: float, pixel_size: float, what: str) -> None:
    """A filter parameter given in meters, converted to pixels, must stay small."""
    radius = value_m / pixel_size
    if not math.isfinite(radius) or radius > MAX_FILTER_RADIUS_PX:
        raise ValueError(f"{what} of {value_m} m is {radius:.0f} px, the limit is {MAX_FILTER_RADIUS_PX}")


def check_contours(contours) -> None:
    if len(contours) > MAX_CONTOURS:
        raise ValueError(f"{len(contours)} contours, the limit is {MAX_CONTOURS}")
    vertices = 0
    for c in contours:
        vertices += len(c)
        if vertices > MAX_VERTICES:
            raise ValueError(f"more than {MAX_VERTICES} contour vertices")
