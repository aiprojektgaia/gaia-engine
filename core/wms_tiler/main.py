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

import argparse
import shutil
import sys
import time
import traceback

import limits

from models.LayerInfo import BoundingBox
from usecase.create_and_store_tile import create_and_store_tile
from usecase.create_tile_boundaries import create_tile_boundaries, \
    apply_overlap, get_tile_size_in_meters, get_unpadded_tile_size_in_meters
from usecase.report_back import report_back


def extract_bounding_box(bounding_box:str) -> BoundingBox:
    bounds = bounding_box.split(',')
    # bounds are: topLeft_x,topLeft_y,bottomRight_x,bottomRight_y
    # translated: min_x, max_y, max_x, min_y
    return BoundingBox(float(bounds[0]), float(bounds[3]), float(bounds[2]), float(bounds[1]))

def start_tiling(wms_server_url:str, layer_name:str,
                 tile_size_in_pixels:int, overlap:int, mpp:float,
                 bounding_box: str, epsg: str,
                 output_path: str, image_format: str,
                 callback_url: str) -> int:

    tiles_created = []
    total_tiles_expected = 0
    try:
        limits.check_wms_url(wms_server_url)
        limits.check_names(layer_name, epsg, image_format)
        deadline = time.monotonic() + limits.WMS_TOTAL_DEADLINE_SECONDS
        bbox = extract_bounding_box(bounding_box)
        # Reject bad geometry and over-quota jobs before any work or allocation.
        limits.validate_tiling_parameters(bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y,
                                          mpp, tile_size_in_pixels, overlap)
        tile_size_in_meters = get_tile_size_in_meters(mpp, tile_size_in_pixels)
        tile_size_no_padding = get_unpadded_tile_size_in_meters(tile_size_in_meters, overlap)
        print(f"tile_size_in_meters: {tile_size_in_meters}")
        print(f"no padding - tile_size_in_meters: {tile_size_no_padding}")
        # create a list of tiles boundaries
        tiles = create_tile_boundaries(bbox, tile_size_no_padding)
        print(f"total tiles created: {len(tiles)}")
        # apply the overlap percentage
        expanded_tiles = apply_overlap(tiles, tile_size_no_padding, overlap)
        total_tiles_expected = len(expanded_tiles)
        print(f"total_tiles_expected: {total_tiles_expected}")

        # Reserve disk up front: worst case per tile, capped by the job budget.
        per_tile_cap = limits.max_tile_response_bytes(tile_size_in_pixels)
        needed = min(total_tiles_expected * per_tile_cap, limits.MAX_JOB_BYTES)
        free = shutil.disk_usage(output_path).free
        if free < needed:
            raise ValueError(f"not enough free disk space for tiling: {free} < {needed} bytes")
        job_bytes = 0

        # per boundary call wms to get the tile
        for tile in expanded_tiles:
            if time.monotonic() > deadline:
                raise TimeoutError("tiling exceeded its total time limit")
            # call wms to get the tile
            # save the tile in the output folder
            remaining = limits.MAX_JOB_BYTES - job_bytes
            tile_path, written = create_and_store_tile(
                wms_server_url, layer_name, output_path, tile, epsg,
                tile_size_in_pixels, image_format, min(per_tile_cap, remaining))
            job_bytes += written
            tiles_created.append(tile_path)

        ## call the callback url with the status of the tiling process
        report_back(callback_url, True, {
            "tiles_created": tiles_created,
            "total_tiles_expected": total_tiles_expected,
        })

        # return number of images created
        return len(tiles_created)
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        report_back(callback_url, False, {
            "tiles_created": tiles_created,
            "total_tiles_expected": total_tiles_expected,
            "error": str(e),
            "traceback": traceback.format_exc()})
        return 0

if __name__ == '__main__':
    #print(f"args size: {len(sys.argv)}")
    # print the arg.sys passed to the script
    #print(f"args: {sys.argv}")

    parser = argparse.ArgumentParser(prog = 'Run tiler against a wms server')
    parser.add_argument('--wms-server-url', type=str, required=True,
                        help='a base wms url. eg: http://localhost:8080/geoserver/wms')
    parser.add_argument('--layer-name', metavar='str', required=True,
                        help='the wms layer name. eg: topp:states')
    parser.add_argument('--tile-size-pixels', metavar='int', type=int, default=1024,
                        help='the height/width of the image in pixels. Its a square. eg: 1024')
    parser.add_argument('--overlap', metavar='int', type=int, default=10,
                        help='a percentage of overlap between tiles. eg: 10')
    parser.add_argument('--mpp', metavar='float', type=float, default=0.08,
                        help='number of meters per pixel, this should be calculated depending on the resolution of the source image. ' +
                             'eg: image is 25000x25000 px and we want a with of 1000m => ppm = 1000/25000 == 0.08. ' +
                             'This means there will be 80m per tile')
    parser.add_argument('--bbox', metavar='string', type=str, required=True,
                        help='the bounding box for the area to be tiled. eg: topLeft_x,topLeft_y,bottomRight_x,bottomRight_y')
    parser.add_argument('--epsg', metavar='str', type=str, required=True,
                        help='the coordinates system of the bounding box. eg: EPSG:3006')
    parser.add_argument('--output-path', metavar='path', type=str, required=True,
                        help='the name of the output folder')
    parser.add_argument('--image-format', metavar='str', type=str, default='geotiff',
                        help='the image format to be saved. eg: geotiff, png, tif')
    parser.add_argument('--callback-url', metavar='str', type=str,
                        help='a callback url, to inform of the status')

    args, unknown_args = parser.parse_known_args()
    print(f"extra args: {unknown_args}")
    start_tiling(args.wms_server_url, args.layer_name, args.tile_size_pixels, args.overlap, args.mpp,
                 args.bbox, args.epsg, args.output_path, args.image_format,
                 args.callback_url)
