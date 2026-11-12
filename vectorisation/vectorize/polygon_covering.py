import shapely
from shapely.strtree import STRtree
from shapely.ops import unary_union
from shapely.geometry import Polygon, MultiPolygon, LineString, box
from shapely.affinity import rotate, translate
from shapely import minimum_rotated_rectangle

from collections import defaultdict
from itertools import combinations
import numpy as np
from math import ceil, degrees, sqrt, atan2
from typing import List, Tuple


def map_to_nearest(remapping_candidates, targets):
    tree = STRtree(targets)
    small_neares_relabel = [(tree.nearest(c), c) for c in remapping_candidates]
    relable_groups = defaultdict(list)
    for nearest, candidate in small_neares_relabel:
        relable_groups[nearest].append(candidate)
    relable_groups = {k: unary_union(v) for k, v in relable_groups.items()}
    for k, v in relable_groups.items():
        targets[k] = targets[k].union(v)
    return targets


def find_uncovered(targets: List[MultiPolygon], bounds: Polygon = None):
    union_target = unary_union(targets)
    if bounds is None:
        bounds = box(*union_target.bounds)
    uncovered = bounds.difference(union_target)
    return uncovered


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


def find_overlaps(targets: List[MultiPolygon]):
    overlaps = []
    for r in range(2, len(targets) + 1):
        for combo in combinations(targets, r):
            intersection = combo[0]
            indices = []
            for mp in combo:
                if intersection.is_empty:
                    break
                intersection = intersection.intersection(mp)
                indices.append(targets.index(mp))
            if not intersection.is_empty:
                intersection = geometry_collection_to_polygons(intersection)
                overlaps.append((intersection, indices))
    return overlaps


def triangulate_and_map_to_nearest(remapping_candidates, targets: List[MultiPolygon]):
    relable_groups = defaultdict(list)
    tree = STRtree(targets)
    for c in remapping_candidates:
        t = triangulate_polygon(c, 4)
        tri_polygons = triangulation_to_polygons(t)
        for p in tri_polygons:
            i = tree.nearest(p)
            relable_groups[i].append(p)
    for k, v in relable_groups.items():
        uuv = unary_union(v)
        print(uuv.is_valid)
        # targets[k] = targets[k].union(unary_union(v))
    relable_groups = {k: unary_union(v) for k, v in relable_groups.items()}
    for k, v in relable_groups.items():
        targets[k] = targets[k].union(v)
        print(targets[k].is_valid)
    return targets


def tile_and_map_to_nearest(
    remapping_candidates, targets: List[MultiPolygon], tile_size=2
):
    relable_groups = defaultdict(list)
    tree = STRtree(targets)
    for c in remapping_candidates:
        tiles = tile_polygon(c, tile_size)
        for t in tiles:
            i = tree.nearest(t)
            relable_groups[i].append(t)

    relable_groups = {k: unary_union(v) for k, v in relable_groups.items()}
    for k, v in relable_groups.items():
        t = targets[k].union(v)
        targets[k] = MultiPolygon(geometry_collection_to_polygons(t))
        print((targets[k]).geom_type)
    return targets


def relable_polygons(
    relabling_candidate: MultiPolygon, targets: List[MultiPolygon], min_area=4
):
    small_candidates = []
    large_candidates = []

    for g in relabling_candidate.geoms:
        if g.area < min_area:
            small_candidates.append(g)
        else:
            large_candidates.append(g)

    targets = map_to_nearest(small_candidates, targets)

    # targets = map_to_nearest(large_candidates, targets)
    # targets = triangulate_and_map_to_nearest(large_candidates, targets)
    # targets = tile_and_map_to_nearest(
    #     large_candidates, targets, tile_size=sqrt(min_area)
    # )
    targets = tile_and_map_to_nearest(large_candidates, targets, tile_size=2)

    return targets


def recursive_tiling(polygon, tile_size=2):
    to_tile = [polygon]
    tiles = []
    while len(to_tile) > 0:
        p = to_tile.pop(0)
        x_min, y_min, x_max, y_max = p.bounds
        x_length = x_max - x_min
        y_length = y_max - y_min
        if x_length < tile_size and y_length < tile_size:
            tiles.append(p)
            continue
        tp = tile_polygon(p, num_tiles=(2, 2))
        to_tile += tp
    return tiles


def tile_polygon(polygon, tile_size=None, num_tiles=None):
    if polygon.area == 0 or polygon.is_empty:
        return []
    if polygon.exterior.is_ccw:
        polygon = shapely.reverse(polygon)
    centroid = polygon.centroid
    rbb = minimum_rotated_rectangle(polygon)
    angle = atan2(
        rbb.exterior.coords[1][1] - rbb.exterior.coords[0][1],
        rbb.exterior.coords[1][0] - rbb.exterior.coords[0][0],
    )

    polygon_rotated = rotate(polygon, -degrees(angle), origin=centroid)

    min_x, min_y, max_x, max_y = polygon_rotated.bounds
    x_length = max_x - min_x
    y_length = max_y - min_y

    if tile_size is None and num_tiles is None:
        raise ValueError("Either tile_size or num_tiles must be provided")
    elif tile_size is not None and num_tiles is not None:
        raise ValueError("Only one of tile_size or num_tiles can be provided")
    elif tile_size is not None:
        x_tiles = int(ceil(x_length / tile_size))
        y_tiles = int(ceil(y_length / tile_size))
    elif num_tiles is not None:
        if isinstance(num_tiles, int):
            x_tiles = num_tiles
            y_tiles = num_tiles
        else:
            x_tiles, y_tiles = num_tiles
    x_tile_size = x_length / x_tiles
    y_tile_size = y_length / y_tiles

    # Step 4: Split the polygon into tiles along the x-axis

    tiles = []
    for x in range(x_tiles):
        for y in range(y_tiles):

            tile = polygon_rotated.intersection(
                box(
                    min_x + x * x_tile_size,
                    min_y + y * y_tile_size,
                    min_x + (x + 1) * x_tile_size,
                    min_y + (y + 1) * y_tile_size,
                )
            )
            if tile.area < 1e-6:
                continue
            elif tile.geom_type == "Polygon":
                tiles.append(tile)
            elif tile.geom_type == "MultiPolygon":
                for t in tile.geoms:
                    tiles.append(t)
            elif tile.geom_type == "GeometryCollection":
                for t in tile.geoms:
                    if t.geom_type == "Polygon":
                        tiles.append(t)
                    elif t.geom_type == "MultiPolygon":
                        for tt in t.geoms:
                            tiles.append(tt)

    # Step 5: Rotate tiles back to the original orientation
    tiles_rotated_back = [
        rotate(tile, degrees(angle), origin=centroid) for tile in tiles
    ]

    return tiles_rotated_back


def cut_out_shape(cutout: MultiPolygon, target: List[MultiPolygon]):
    outline = unary_union([box(*p.bounds) for p in target])
    cutout = cutout.intersection(outline)
    for i, t in enumerate(target):
        target[i] = t.difference(cutout)
    return target, cutout
