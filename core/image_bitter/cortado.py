from pathlib import Path

import numpy as np
import rasterio
from helpers.logger import log

'''
this file has the methods to read, write and manipulate an image file
to finally create a version of it where only certain values are kept.
Anything under a threshold is set to 0 
'''

def load_mask(image_path, as_bitmask=False):
    with rasterio.open(image_path) as src:
        mask = src.read(1)
        transform = src.transform
    if as_bitmask:
        mask = mask > 0
        mask.astype(bool)
    return mask, transform

def read_image(image_path)-> (np.array, rasterio.transform, rasterio.profiles):
    with rasterio.open(image_path) as src:
        band_one = src.read(1)
        transform = src.transform
        profile = src.profile

    return band_one, transform, profile

def get_image_resolution(image_path)-> (float, float):
    with rasterio.open(image_path) as src:
        transform = src.transform
        image_geo_info = parse_geo_info(transform)
        dx = image_geo_info['dx']
        dy = image_geo_info['dy']

    return dx, dy

def print_none_zero_values(band_one: np.array):
    log("None zero values:")
    log(band_one[band_one > 0])
    min_val = 0
    max_val = 256
    counter = 0
    for i in range(0, len(band_one)):
        for j in range(0, len(band_one[0])):
            if band_one[i][j] > 0:
                counter += 1
                if band_one[i][j] < min_val:
                    min_val = band_one[i][j]
                if band_one[i][j] > max_val:
                    max_val = band_one[i][j]

    log(f"min_val: {min_val}, max_val: {max_val}, counter: {counter}")


def apply_confidence_level(band_one: np.array, min_confidence: float):
    band_one[band_one < min_confidence] = 0
    return band_one


def create_bitmap_file(band_one: np.array, file_profile: rasterio.profiles,
                       image_name: str, output_path: Path) -> Path:
    target_file = output_path / image_name
    file_profile.update(count = 1)
    with rasterio.open(target_file, "w", **file_profile) as dest:
        dest.write(band_one,indexes = 1)

    return target_file

def parse_geo_info(transform: rasterio.transform):
    return {'dx':transform[0],
            'xrot':transform[1],
            'x0':transform[2],
            'yrot':transform[3],
            'dy':transform[4],
            'y0':transform[5]}
