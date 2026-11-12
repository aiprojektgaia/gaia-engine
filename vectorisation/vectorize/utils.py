from shapely.geometry import Polygon, MultiPolygon
from typing import Union

import numpy as np
import tqdm

from simplification.cutil import (
    simplify_coords,
    simplify_coords_vwp,
)


def simplify_contours(
    contours: Union[Polygon, MultiPolygon], tolerance, algorithm="vw"
) -> Union[Polygon, MultiPolygon]:
    if algorithm not in ["rdp", "vw"]:
        raise ValueError(
            f"Invalid algorithm: {algorithm}\nValid options are 'rdp'(Ramer–Douglas–Peucker) and 'vw'  Visvalingam-Whyatt)"
        )
    if tolerance <= 0:
        return contours
    if contours.geom_type == "Polygon":
        return simplify_polygon(contours, tolerance, algorithm)
    else:
        return simplify_multipolygon(contours, tolerance, algorithm)


def buffer_contours(contours, buffer) -> MultiPolygon:
    if buffer == 0:
        return contours
    buffered_contours = []
    for p in contours.geoms:
        buffered_contours.append(p.buffer(buffer).buffer(-buffer))
    return MultiPolygon(buffered_contours)


def simplify_polygon(polygon, tolerance, method="vw"):
    method_map = {
        "vw": simplify_coords_vwp,
        "rdp": simplify_coords,
    }
    if method not in method_map:
        raise ValueError(f"Invalid method {method}")
    _fn = method_map[method]
    coords = np.array(polygon.exterior.coords)
    hole_coords = [np.array(hole.coords) for hole in polygon.interiors]
    simplified_coords = _fn(coords, tolerance)
    simplified_holes = []
    for hole in hole_coords:
        simplified_hole = _fn(hole, tolerance)
        if len(simplified_hole) > 2:
            simplified_holes.append(simplified_hole)
    # print(simplified_coords)
    return Polygon(simplified_coords, simplified_holes)


def simplify_multipolygon(multipolygon, tolerance, method="vw"):
    print("simplifying multipolygon")
    return MultiPolygon(
        [simplify_polygon(poly, tolerance, method) for poly in multipolygon.geoms]
    )


def geometry_collection_to_polygons(gc):
    if gc.geom_type == "Polygon":
        return [gc]
    if gc.geom_type == "MultiPolygon":
        return [g for g in gc.geoms]
    elif gc.geom_type == "GeometryCollection":
        poly = [g for g in gc.geoms if g.geom_type == "Polygon"]
        mp = [g for g in gc.geoms if g.geom_type == "MultiPolygon"]
        if len(mp) > 0:
            poly += [g for g in mp.geoms]
        return poly
