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

"""Pre-flight limits for raster batches. Override with environment variables."""

import math
import os
import shutil

from osgeo import gdal

MAX_FILES = int(os.environ.get("GAIA_RASTER_MAX_FILES", 10_000))
MAX_PIXELS_PER_FILE = int(os.environ.get("GAIA_RASTER_MAX_FILE_PIXELS", 100_000_000))
MAX_MOSAIC_PIXELS = int(os.environ.get("GAIA_RASTER_MAX_MOSAIC_PIXELS", 2_000_000_000))
MAX_MOSAIC_SIDE = int(os.environ.get("GAIA_RASTER_MAX_MOSAIC_SIDE", 200_000))
# Byte budgets: pixels alone undercount wide data types and multi-band files.
MAX_FILE_BYTES = int(os.environ.get("GAIA_RASTER_MAX_FILE_BYTES", 400 * 1024**2))
MAX_MOSAIC_BYTES = int(os.environ.get("GAIA_RASTER_MAX_MOSAIC_BYTES", 4 * 1024**3))


def _bytes_per_pixel(ds) -> int:
    """Decoded bytes for one pixel across all bands."""
    total = 0
    for i in range(1, ds.RasterCount + 1):
        total += gdal.GetDataTypeSize(ds.GetRasterBand(i).DataType) // 8
    return max(total, 1)


def check_file_count(files) -> None:
    if len(files) == 0:
        raise ValueError("no raster files to process")
    if len(files) > MAX_FILES:
        raise ValueError(f"{len(files)} raster files, the limit is {MAX_FILES}")


def check_file_size(path) -> None:
    """Reject a raster by its header before anything is decoded."""
    gdal.UseExceptions()
    ds = gdal.Open(str(path))
    try:
        pixels = ds.RasterXSize * ds.RasterYSize
        decoded = pixels * _bytes_per_pixel(ds)
    finally:
        ds = None
    if pixels > MAX_PIXELS_PER_FILE:
        raise ValueError(f"{path} has {pixels} pixels, the limit is {MAX_PIXELS_PER_FILE}")
    if decoded > MAX_FILE_BYTES:
        raise ValueError(f"{path} decodes to {decoded} bytes, the limit is {MAX_FILE_BYTES}")


def check_mosaic(files, x_resolution, y_resolution, output_dir=None) -> None:
    """Predict the mosaic's dimensions and size in bytes from the inputs'
    extents, band counts and data types; reject oversized ones and make sure
    the output disk can hold the result."""
    check_file_count(files)
    gdal.UseExceptions()
    if not (math.isfinite(x_resolution) and math.isfinite(y_resolution)
            and x_resolution != 0 and y_resolution != 0):
        raise ValueError("mosaic resolution must be finite and non-zero")
    min_x = min_y = math.inf
    max_x = max_y = -math.inf
    bytes_per_pixel = 1
    for f in files:
        ds = gdal.Open(str(f))
        try:
            bytes_per_pixel = max(bytes_per_pixel, _bytes_per_pixel(ds))
            ulx, xres, _, uly, _, yres = ds.GetGeoTransform()
            lrx = ulx + ds.RasterXSize * xres
            lry = uly + ds.RasterYSize * yres
        finally:
            ds = None
        min_x, max_x = min(min_x, ulx, lrx), max(max_x, ulx, lrx)
        min_y, max_y = min(min_y, uly, lry), max(max_y, uly, lry)
    width = (max_x - min_x) / abs(x_resolution)
    height = (max_y - min_y) / abs(y_resolution)
    if not (math.isfinite(width) and math.isfinite(height)) \
            or width > MAX_MOSAIC_SIDE or height > MAX_MOSAIC_SIDE \
            or width * height > MAX_MOSAIC_PIXELS:
        raise ValueError(f"mosaic of {width:.0f}x{height:.0f} pixels exceeds the limits")
    mosaic_bytes = width * height * bytes_per_pixel
    if mosaic_bytes > MAX_MOSAIC_BYTES:
        raise ValueError(f"mosaic would be {mosaic_bytes:.0f} bytes, the limit is {MAX_MOSAIC_BYTES}")
    if output_dir is not None:
        free = shutil.disk_usage(str(output_dir)).free
        if free < mosaic_bytes:
            raise ValueError(f"not enough free disk for the mosaic: {free} < {mosaic_bytes:.0f} bytes")
