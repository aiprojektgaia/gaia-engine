from .growing_rectangles import grow_footprint

import cv2

import vector_limits
import rasterio
import rasterio.io
import rasterio.mask
import rasterio.transform


from shapely.geometry import Polygon, MultiPolygon, box, mapping
from shapely.affinity import affine_transform

import numpy as np

import tempfile

from typing import List, Tuple

from tqdm import tqdm


def get_building_masks(
    building_masks: np.ndarray,
    transform: rasterio.transform.Affine,
    smallest_building: float,
    shotest_wall: float = 1,
) -> List[Tuple[np.ndarray, rasterio.transform.Affine]]:
    clipped_building_masks = []

    pixel_size = abs(transform.a)
    smallest_mask = smallest_building / pixel_size**2
    building_masks = building_masks.astype(np.uint8)
    contours = cv2.findContours(
        building_masks, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    vector_limits.check_contours(contours[0])
    large_contours = [c for c in contours[0] if cv2.contourArea(c) > smallest_mask]
    # each contour is clipped into its own crop; bound the total crop area
    crop_pixels = 0
    for c in large_contours:
        _, _, w, h = cv2.boundingRect(c)
        crop_pixels += (w + 2) * (h + 2)
        if crop_pixels > vector_limits.MAX_CROP_PIXELS:
            raise ValueError("building crops exceed the vectorisation budget")
    # In-memory dataset: nothing is written to disk, so nothing can leak.
    with rasterio.io.MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff",
            height=building_masks.shape[0],
            width=building_masks.shape[1],
            count=1,
            dtype=np.uint8,
            transform=transform,
            compress="lzw",
        ) as dst:
            dst.write(building_masks, 1)

        with memfile.open() as rio_src:
            for c in tqdm(large_contours, desc="Clipping building masks"):
                contour_bounds = cv2.boundingRect(c)
                poly_contour = Polygon(c.reshape(-1, 2))
                poly_contour = affine_transform(poly_contour, transform.to_shapely())

                clip_img, clip_transform = rasterio.mask.mask(
                    rio_src, [poly_contour], crop=True, pad=True
                )
                clipped_building_masks.append((clip_img.squeeze(), clip_transform))
    return clipped_building_masks


def vectorize_building_masks(
    mask: np.ndarray,
    transform: rasterio.transform.Affine,
    smallest_area=5,
    shortest_wall=1,
    apply_smoothing=False,
) -> MultiPolygon:
    # t = [
    #     transform.a,
    #     transform.b,
    #     transform.d,
    #     transform.e,
    #     transform.xoff,
    #     transform.yoff,
    # ]

    building_footprint = []
    length_scaler = transform.a

    clipped_building_masks = get_building_masks(mask, transform, smallest_area)
    shortest_wall = shortest_wall / length_scaler
    smallest_area = smallest_area / (length_scaler**2)
    for c, t in tqdm(clipped_building_masks, desc="Vectorizing building masks"):

        fp = grow_footprint(c, smallest_area, shortest_wall, apply_smoothing)
        fp = affine_transform(fp, t.to_shapely())
        building_footprint.append(fp)
    return MultiPolygon(building_footprint)
