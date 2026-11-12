from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from file_merger import merge_files


def create_tile(matrix: list[list[int]], tile_size: int = 10, image_name:str = "results\\test.tif"):
    # Define the size of the tile
    width, height = tile_size, tile_size

    image_path = Path(image_name)
    # Create an array with the desired size and fill it with zeros
    #data = np.zeros((height, width), dtype=rasterio.uint8)
    data = np.array(matrix)

    # Define the transform (affine transformation matrix)
    transform = from_origin(142000.0, 6393000.0, 1, 1)  # top-left corner at (0, 10), pixel size 1x1

    # Define the profile (metadata) for the new TIFF file
    profile = {
        'driver': 'GTiff',
        'dtype': 'uint8',
        'nodata': 0,
        'width': width,
        'height': height,
        'count': 1,  # number of bands
        'crs': 'EPSG:3007',  # coordinate reference system
        'transform': transform
    }

    # Create the new TIFF file
    with rasterio.open(image_path, 'w', **profile) as dst:
        dst.write(data, 1)

def test_merge_tiles():
    matrix_one = [[0, 0, 0], [1, 0, 1], [1, 1, 1]]
    matrix_two = [[1, 0, 1], [0, 1, 0], [0, 0, 0]]
    create_tile(matrix_one, 3, "results\\test-one.tif")
    create_tile(matrix_two, 3, "results\\test-two.tif")
    matrix_expected = [[1, 0, 1], [1, 1, 1], [1, 1, 1]]

    merged_file = merge_files(["results\\test-one.tif", "results\\test-two.tif"], Path("results"))

    with rasterio.open( merged_file) as src:
        assert src.width == 3
        assert src.height == 3
        assert src.transform == from_origin(142000.0, 6393000.0, 1, 1)
        #assert src.read(1).tolist() == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        print(src.read(1).tolist())
        assert src.read(1).tolist() == matrix_expected
