import logging

import json
import math
import os

import limits

import numpy as np
import geopandas as gpd
from numpy.typing import ArrayLike
import cv2

logger = logging.getLogger(__name__)


class GeoObject:
    """Object that holds the world coordinates of a segment"""

    def __init__(self, x: ArrayLike, y: ArrayLike, color: np.uint8 = 255):
        """
        Parameters
        ----------
        x : ArrayLike[floats]
            list of x-coordinates of the polygon vertices
        x : ArrayLike[floats]
            list of y-coordinates of the polygon vertices
        """
        self.xcoords = x
        self.ycoords = y
        self.color = color

        # compute bounding box of the element
        self.bounding_box = [np.min(x), np.min(y), np.max(x), np.max(y)]
        # collect both x- and y-coordinate
        self.coords = [(self.xcoords[k], self.ycoords[k])
                       for k in range(len(self.xcoords))]


class GeoPolygonObject(GeoObject):
    def draw(self, image, points):
        cv2.fillPoly(image, pts=[points], color=self.color)


class GeoLineObject(GeoObject):
    def draw(self, image, points):
        cv2.polylines(image, [points], False, color=self.color)


MAX_BASEMAP_BYTES = int(os.environ.get("GAIA_COMPARE_MAX_BASEMAP_BYTES", 64 * 1024 * 1024))
MAX_BASEMAP_FEATURES = int(os.environ.get("GAIA_COMPARE_MAX_FEATURES", 20_000))


def _reject_constant(name):
    # Python's json accepts NaN/Infinity; coordinates must be finite numbers.
    raise ValueError(f"basemap contains a non-finite number ({name})")


def _count_parts(node: dict) -> int:
    """Rings and lines a geometry contributes (members of multi-geometries
    and polygon holes each count), so a few features cannot smuggle in
    millions of parts."""
    kind = node.get("type")
    coords = node.get("coordinates")
    if not isinstance(coords, list):
        return 1 if kind == "GeometryCollection" else 0
    if kind in ("LineString", "MultiPoint"):
        return 1
    if kind in ("Polygon", "MultiLineString"):
        return len(coords)
    if kind == "MultiPolygon":
        return sum(len(p) if isinstance(p, list) else 1 for p in coords)
    return 0


def _check_structure(doc) -> None:
    """Walk the parsed GeoJSON once, iteratively, before geopandas/shapely see
    it: bound nesting depth, total coordinates and geometry parts, and require
    every coordinate to be a finite number."""
    coordinates = 0
    parts = 0
    stack = [(doc, 0)]
    while stack:
        node, depth = stack.pop()
        if depth > limits.MAX_JSON_DEPTH:
            raise ValueError("basemap is nested too deeply")
        if isinstance(node, dict):
            parts += _count_parts(node)
            if parts > limits.MAX_GEOMETRY_PARTS:
                raise ValueError("basemap has too many geometry parts")
            stack.extend((v, depth + 1) for v in node.values())
        elif isinstance(node, list):
            if node and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in node):
                # a position: [x, y] or [x, y, z]
                coordinates += 1
                if coordinates > limits.MAX_BASEMAP_COORDINATES:
                    raise ValueError("basemap has too many coordinates")
                if not all(math.isfinite(v) for v in node):
                    raise ValueError("basemap contains a non-finite coordinate")
            else:
                stack.extend((v, depth + 1) for v in node)


def _read_basemap(source: str, bbox=None) -> gpd.GeoDataFrame:
    """Load a GeoJSON basemap from a local file or a GeoJSON string.

    The source is parsed here instead of being handed to GDAL/geopandas, which
    would treat a string such as 'http://...' or '/vsicurl/...' as a remote
    data source and fetch it.
    """
    text = str(source)
    if not text.lstrip().startswith(('{', '[')):
        if '://' in text or text.startswith('/vsi'):
            raise ValueError('basemap must be a local file or a GeoJSON document')
        with open(text, 'r', encoding='utf-8') as f:
            text = f.read(MAX_BASEMAP_BYTES + 1)
    if len(text) > MAX_BASEMAP_BYTES:
        raise ValueError('basemap is larger than the allowed size')
    doc = json.loads(text, parse_constant=_reject_constant)
    _check_structure(doc)
    if isinstance(doc, dict) and doc.get('type') == 'FeatureCollection':
        features = doc.get('features')
    elif isinstance(doc, dict) and doc.get('type') == 'Feature':
        features = [doc]
    else:
        raise ValueError('basemap must be a GeoJSON Feature or FeatureCollection')
    if not isinstance(features, list):
        raise ValueError('basemap features must be a list')
    if len(features) > MAX_BASEMAP_FEATURES:
        raise ValueError(f'{len(features)} basemap features, the limit is {MAX_BASEMAP_FEATURES}')
    data = gpd.GeoDataFrame.from_features(features)
    if 'geometry' not in data:
        return gpd.GeoDataFrame(geometry=[])
    if bbox is not None:
        xmin, ymin, xmax, ymax = [float(v) for v in bbox]
        data = data.cx[xmin:xmax, ymin:ymax]
    return data


def getObjects(file: str, bounding_box: ArrayLike) -> list[GeoObject]:
    """Returns a list of object from a map file in a specific area

    Parameters
    ----------
    file : str
        filename or geojson-string
    bounding_box : ArrayLike of floats
        (xmin,ymin,xmax,ymax) coordinates of the upper left and lower right corner

    Returns
    -------
    list[GeoObject]
        list of GeoObject
    """
    data = _read_basemap(file, bbox=bounding_box)

    # creates one GeoObject from each polygon or line and add it to the list
    objects = []
    skipped = {}
    for objlist in data.geometry:
        # Rows with missing or empty geometry are common in real basemaps.
        if objlist is None or objlist.is_empty:
            skipped['null/empty'] = skipped.get('null/empty', 0) + 1
            continue

        if objlist.geom_type == 'MultiPolygon':
            for obj in objlist.geoms:
                xx, yy = obj.exterior.coords.xy
                if np.max(xx)-np.min(xx) > 0.2 and np.max(yy)-np.min(yy) > 0.2:
                    objects.append(GeoPolygonObject(xx, yy))
                    # Interior rings are drawn in the background colour, so they
                    # only make sense once their own exterior has been drawn.
                    # Emitting them for a filtered-out polygon would subtract
                    # from whatever else happens to occupy that area.
                    for ring in obj.interiors:
                        rx, ry = ring.coords.xy
                        objects.append(GeoPolygonObject(rx, ry, color=0))
        elif objlist.geom_type == 'Polygon':
            xx, yy = objlist.exterior.coords.xy
            objects.append(GeoPolygonObject(xx, yy))
            for ring in objlist.interiors:
                rx, ry = ring.coords.xy
                objects.append(GeoPolygonObject(rx, ry, color=0))
        elif objlist.geom_type == 'MultiLineString':
            for obj in objlist.geoms:
                xx, yy = obj.coords.xy
                objects.append(GeoLineObject(xx, yy))
        elif objlist.geom_type == 'LineString':
            xx, yy = objlist.coords.xy
            objects.append(GeoLineObject(xx, yy))
        else:
            # Unsupported geometry is skipped, not fatal. The basemap is
            # supplied by the user, and one stray feature must not abort the
            # whole run - a raise here propagates up and kills every remaining
            # task in the project run.
            skipped[objlist.geom_type] = skipped.get(objlist.geom_type, 0) + 1

    if skipped:
        summary = ', '.join(f'{count}x {kind}' for kind, count in sorted(skipped.items()))
        logger.warning('Skipped unsupported geometry in %s: %s', file, summary)

    return objects


def getMergedObjects(file: str) -> list[GeoObject]:
    """
    Parameters
    ----------
    file : str
        filename or geojson-string

    Returns
    -------
    list of GeoObject
    """
    data = _read_basemap(file)
    # combining objects that shares at least one edge (or part of edge)
    objlist = data.geometry.buffer(0.1).unary_union.buffer(-0.1)

    # creates one GeoObject from each polygon and add it to the list
    objects = []
    if objlist.geom_type == 'MultiPolygon':
        for obj in objlist.geoms:
            xx, yy = obj.exterior.coords.xy
            if np.max(xx)-np.min(xx) > 0.2 and np.max(yy)-np.min(yy) > 0.2:
                objects.append(GeoPolygonObject(xx, yy))
    elif objlist.geom_type == 'Polygon':
        xx, yy = objlist.exterior.coords.xy
        objects.append(GeoPolygonObject(xx, yy))

    return objects
