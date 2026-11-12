import os

import cv2
import numpy as np
import rasterio
import fiona
import shapely
from shapely.geometry import MultiPolygon


MAX_MASK_PIXELS = int(os.environ.get("GAIA_VECTORIZE_MAX_PIXELS", 400_000_000))


def load_mask(image_path, as_bitmask=False):
    with rasterio.open(image_path) as src:
        # Refuse oversized rasters from the header, before decoding the band.
        if src.width * src.height > MAX_MASK_PIXELS:
            raise ValueError(
                f"{image_path} has {src.width * src.height} pixels, the limit is {MAX_MASK_PIXELS}")
        # Masks are single-band 8-bit likelihoods; anything else (wider types,
        # extra bands) would multiply memory beyond the pixel budget.
        if src.count != 1 or src.dtypes[0] != "uint8":
            raise ValueError(
                f"{image_path} must be a single-band uint8 mask, got {src.count} band(s) of {src.dtypes[0]}")
        mask = src.read(1)
        transform = src.transform
    if as_bitmask:
        mask = mask > 0
        mask.astype(bool)
    return mask, transform


def write_mask(mask, transform, out_path):

    with rasterio.open(
        out_path,
        "w",
        driver="GTiff",
        height=mask.shape[0],
        width=mask.shape[1],
        count=1,
        dtype=np.uint8,
        transform=transform,
        compress="lzw",
    ) as dst:
        dst.write(mask, 1)


def valided_and_filter_contour(contour, smallets_area=0, smallest_hole=0):

    if contour.geom_type == "Polygon":
        contour = MultiPolygon([contour])
    if contour.geom_type == "GeometryCollection":
        poly = [g for g in contour.geoms if g.geom_type == "Polygon"]
        mp = [g for g in contour.geoms if g.geom_type == "MultiPolygon"]
        if len(mp) > 0:
            poly += [g for g in mp.geoms]
        contour = MultiPolygon(poly)

    contour = MultiPolygon([g for g in contour.geoms if g.is_valid and g.area > 0])

    if smallets_area > 0:
        contour = MultiPolygon([g for g in contour.geoms if g.area > smallets_area])
    if smallest_hole > 0:
        new_contours = []
        for g in contour.geoms:
            interior_list = []
            for interior in g.interiors:
                if interior.area > smallest_hole:
                    interior_list.append(interior)
            new_contours.append(shapely.geometry.Polygon(g.exterior, interior_list))
        contour = MultiPolygon(new_contours)
    return contour


def write_contours(contours, layer_name, out_path):
    if isinstance(contours, MultiPolygon):
        contours = [contours]
    if isinstance(layer_name, str):
        layer_name = [layer_name]
    if len(layer_name) != len(contours):
        layer_name = [f"layer_{i}" for i in range(len(contours))]

    with fiona.open(
        out_path,
        "w",
        driver="GPKG",
        schema={
            "geometry": "MultiPolygon",
            "properties": {"id": "int", "layer": "str"},
        },
    ) as c:
        for i, (p, l) in enumerate(zip(contours, layer_name)):

            c.write(
                {
                    "geometry": shapely.geometry.mapping(p),
                    "properties": {"id": i, "layer": l},
                }
            )
