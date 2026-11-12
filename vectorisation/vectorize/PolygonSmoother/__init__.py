from .smoother import _polygon_smoothing
from shapely.geometry import Polygon, MultiPolygon
import numpy as np

from simplification.cutil import (
    simplify_coords,
    simplify_coords_idx,
    simplify_coords_vw,
    simplify_coords_vw_idx,
    simplify_coords_vwp,
)


def smooth_polygon(polygon: Polygon, method, subdivide=0, *args, **kwargs):
    return _polygon_smoothing(polygon, method, subdivide, *args, **kwargs)


def smooth_multipolygon(
    multipolygon: MultiPolygon, method, subdivide=0, *args, **kwargs
):
    smoothed_polys = []
    for poly in multipolygon.geoms:
        smoothed_polys.append(smooth_polygon(poly, method, subdivide, *args, **kwargs))
    return MultiPolygon(smoothed_polys)


def simplify_polygon(polygon, tolerance, method="vw"):
    method_map = {
        "vw": simplify_coords_vw,
        "vwp": simplify_coords_vwp,
        "rdp": simplify_coords,
    }
    if method not in method_map:
        raise ValueError(f"Invalid method {method}")
    _fn = method_map[method]
    coords = np.array(polygon.exterior.coords)
    hole_coords = [np.array(hole.coords) for hole in polygon.interiors]
    simplified_coords = _fn(coords, tolerance)
    if len(simplified_coords) < 3:
        return Polygon()
    simplified_holes = []
    for hole in hole_coords:
        simplified_hole = _fn(hole, tolerance)
        if len(simplified_hole) > 2:
            simplified_holes.append(simplified_hole)
    # print(simplified_coords)
    return Polygon(simplified_coords, simplified_holes)


def simplify_multipolygon(multipolygon, tolerance, method="vw"):
    return MultiPolygon(
        [simplify_polygon(poly, tolerance, method) for poly in multipolygon.geoms]
    )
