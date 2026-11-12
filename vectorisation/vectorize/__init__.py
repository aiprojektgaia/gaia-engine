import cv2
import numpy as np

import vector_limits
from skimage.measure import find_contours

import shapely
from shapely.geometry import Polygon, MultiPolygon
from shapely.affinity import affine_transform, translate
from shapely.ops import unary_union

from typing import Union, List, Tuple

from .utils import simplify_contours, buffer_contours
from tqdm import tqdm

from .polygon_covering import (
    find_uncovered,
    relable_polygons,
    find_overlaps,
    cut_out_shape,
)


def get_contours(
    mask, min_area=0, transform=None, move_to_origin=False
) -> MultiPolygon:
    # Count contours and vertices cheaply first (OpenCV), so a fragmented mask
    # is refused before skimage and Shapely build millions of objects.
    preflight, _ = cv2.findContours(
        (mask > 0.2).astype(np.uint8),  # same level as find_contours below
        cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    vector_limits.check_contours(preflight)
    del preflight

    mask = np.pad(mask, 1, mode="constant", constant_values=0)
    contour_collection = find_contours(
        mask, 0.2, fully_connected="low", positive_orientation="high"
    )
    contour_shells = []
    contour_holes = []
    for c in tqdm(contour_collection):
        # flip x and y to match the geo coordinates
        c = c[:, [1, 0]]
        p = Polygon(c)
        if not p.is_valid:
            p = p.buffer(0)
            p = shapely.make_valid(p)

        if p.is_valid:
            # compensate for padding
            p = translate(p, xoff=-1, yoff=-1)
            if transform:
                p = affine_transform(p, transform.to_shapely())
            if p.area > min_area:
                if p.exterior.is_ccw:
                    contour_shells.append(p)
                else:
                    contour_holes.append(p)
        else:
            print("invalid polygon")
    print("staring holes union")
    union_holes = unary_union(contour_holes)
    print("starting shells union")
    union_shells = unary_union(contour_shells)
    print("starting difference")
    if len(contour_holes) > 0:
        mp = union_shells.difference(union_holes)
    else:
        mp = union_shells

    if move_to_origin:
        minx, miny, maxx, maxy = mp.bounds
        mp = translate(mp, xoff=-minx, yoff=-miny)
    if mp.geom_type == "Polygon":
        mp = MultiPolygon([mp])
    if min_area > 0 and hasattr(mp, "geoms"):
        mp = MultiPolygon([p for p in mp.geoms if p.area > min_area])
    return mp


def validade_and_clean(contours: MultiPolygon, min_area=0, min_hole_area=0):
    cleaned_contours = []
    for p in contours.geoms:
        if p.is_valid:
            if p.area > min_area:
                cleaned_contours.append(p)

    return MultiPolygon(cleaned_contours)


def complete_cover(
    layers: List[MultiPolygon], smallest_missing=4
) -> List[MultiPolygon]:
    missing_contours = find_uncovered(layers)
    filled_missing = relable_polygons(missing_contours, layers, smallest_missing)

    overlaps = find_overlaps(filled_missing)
    for geoms, idxs in overlaps:
        g = unary_union(geoms)
        for idx in idxs:
            filled_missing[idx] = filled_missing[idx].difference(g)

        tmp_filled_missing = relable_polygons(
            g, [filled_missing[idx] for idx in idxs], 2
        )
        for idx, f in zip(idxs, tmp_filled_missing):
            filled_missing[idx] = f

    return filled_missing


def cut_covering(cutout: MultiPolygon, target: List[MultiPolygon]):
    return cut_out_shape(cutout, target)
