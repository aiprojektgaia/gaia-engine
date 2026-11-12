import argparse
import traceback
from pathlib import Path
import os

from osgeo import gdal
import glob

import raster_limits
from cortado import get_image_resolution

from helpers.logger import enable_logging, log, log_error

"""
# Merge small files into one big file:

This file will take several files and try to combine them into one.
In case of overlapping results, the one with the highest value will be used.
In the end, the result will be saved to a file with the highest possible size.
"""


def merge_files(
    files_list: list[str],
    output_path: Path,
    x_resolution: float = 1,
    y_resolution: float = -1,
) -> str:
    raster_limits.check_mosaic(files_list, x_resolution, y_resolution, output_path)
    output_name = get_name(files_list[0])
    output_file = output_path / f"{output_name}.tif"
    gdal.UseExceptions()
    # build virtual raster and convert to geotiff
    vrt = gdal.BuildVRT(str(output_path / f"{output_name}.vrt"), files_list)
    gdal.Translate(str(output_file), vrt, xRes=x_resolution, yRes=y_resolution)
    vrt = None

    return str(output_file)


def get_name(file_name: str) -> str:
    try:
        # remove the bit_ prefix and the .tif suffix
        name = Path(file_name).name.replace("bit_", "").replace(".tif", "")

        name_parts = name.split("_")
        if len(name_parts) > 2:
            # concatenate all the parts but the last two (the last two are the x and y coordinates)
            name = "_".join(name_parts[:-2])

        return f"result_{name}"
    except Exception as ne:
        log(ne)
        log(traceback.format_exc())
        return "merged_bit"


def merge_brute_force(input_path: Path, output_path: Path) -> str:
    file_struc = str(input_path / "*.tif")
    files_list = glob.glob(file_struc)
    log(files_list)
    raster_limits.check_file_count(files_list)

    output_name = get_name(files_list[0])

    dx, dy = get_image_resolution(files_list[0])
    log(f"dx: {dx}, dy: {dy}")
    raster_limits.check_mosaic(files_list, dx, dy, output_path)

    gdal.UseExceptions()
    # build virtual raster and convert to geotiff
    vrt = gdal.BuildVRT(str(output_path / f"{output_name}.vrt"), files_list)
    gdal.Translate(str(output_path / f"{output_name}.tif"), vrt, xRes=dx, yRes=dy)
    vrt = None

    output_path = output_path / f"{output_name}.tif"
    return output_path.name


def get_file_resolution(file_path: Path) -> tuple:
    src = gdal.Open(str(file_path))
    ulx, xres, xskew, uly, yskew, yres = src.GetGeoTransform()
    lrx = ulx + (src.RasterXSize * xres)
    lry = uly + (src.RasterYSize * yres)
    return ulx, uly, lrx, lry


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Run Merge of files")
    parser.add_argument("--image-path", type=str, help="the image name (with path)")
    parser.add_argument("--output-path", type=str, help="the path for the output file")
    parser.add_argument(
        "--enable-logging",
        type=bool,
        default=False,
        help="enable only for debugging purposes",
    )

    args, unknown_args = parser.parse_known_args()
    # log(f"unknown args = {unknown_args}")
    try:
        if args.enable_logging is True:
            enable_logging()

        merge_brute_force(Path(args.image_path), Path(args.output_path))
    except Exception as e:
        log_error(e, traceback.format_exc())
