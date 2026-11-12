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

from raster_cleaner import clean_mask
from vectorize import get_contours, complete_cover, cut_out_shape
from building_vectorizer import vectorize_building_masks
from vectorize.PolygonSmoother import smooth_multipolygon, simplify_multipolygon

from gaia_io import load_mask, write_mask, write_contours


from pathlib import Path
import json


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Process some masks.")
    parser.add_argument(
        "config_file",
        nargs="?",
        default="config.json",
        help="Path to the configuration file (default: config.json)",
    )
    args = parser.parse_args()
    if not Path(args.config_file).exists():
        print(f"Configuration file {args.config_file} not found")
        exit(1)
    with open(args.config_file, "r") as f:
        config = json.load(f)

    output_dir = Path(config.get("output_dir", "."))
    output_dir.mkdir(exist_ok=True, parents=True)
    WRITE_INTERMEDIATE = config.get("write_intermediate", False)

    ortho_photo = Path(config["raster_files"]["orthophoto"])
    segementation_layers = list((config["raster_files"]["segmentation_layers"]).keys())

    seg_masks = {}
    contours = {}
    for layer in segementation_layers:
        mask, transform = load_mask(
            Path(config["raster_files"]["segmentation_layers"][layer])
        )
        pixel_size = transform.a

        layer_properties = config["layer_properties"][layer]

        min_area = layer_properties.get("min_area", 0)
        min_hole = layer_properties.get("smallest_hole", 0)
        shortest_edge = layer_properties.get("shortest_edge", 0)
        sigma = layer_properties.get("sigma", 0)
        gap_closure = layer_properties.get("gap_closure", 0)

        mask = clean_mask(
            mask, min_area, min_hole, gap_closure, pixel_size, sigma=sigma
        )

        if WRITE_INTERMEDIATE:
            write_mask(
                mask,
                transform,
                Path(output_dir / f"{layer}_cleaned.tif"),
            )

        vectorizer_function = layer_properties.get("vectorizer", None)
        if vectorizer_function == "building":
            print(f"Vectorizing {layer} as building")
            contour = vectorize_building_masks(
                mask, transform, min_area, shortest_edge, False
            )
        else:
            contour = get_contours(mask, min_area, transform)
        if WRITE_INTERMEDIATE:
            write_contours(
                [contour], [layer], output_dir / f"{layer}_contours_no_smoothing.gpkg"
            )

        smoothing = layer_properties.get("smoothing", False)
        if smoothing and smoothing.lower() == "none":
            smoothing = False
        if smoothing:
            subdivide = layer_properties.get("subdivide", 0)
            if "smoothing_parameter" not in layer_properties:
                print(
                    f"Warning: missing smoothing_parameter for layer {layer}, not smoothing"
                )
            else:
                smoothing_parameter = layer_properties["smoothing_parameter"]
                contour = smooth_multipolygon(
                    contour, smoothing, subdivide, smoothing_parameter
                )

        simplify = layer_properties.get("simplify", False)
        if simplify and simplify.lower() == "none":
            simplify = False
        if simplify:
            tol = layer_properties.get("simplify_tolerance", 0)
            if tol <= 0:
                print(f"Warning: missing tolerance for layer {layer}, not simplifying")
            else:
                contour = simplify_multipolygon(contour, tol, simplify)

        if WRITE_INTERMEDIATE:
            write_contours(
                [contour],
                [layer],
                output_dir / f"{layer}_contours_smoothed.gpkg",
            )
        contours[layer] = (contour, transform)
    layer_ordering = config.get("vector_layer_order", {})
    base_layers = config["vector_layer_order"].get("base_layers", [])
    print(f"base_layers {base_layers}")
    overlay_layers = config["vector_layer_order"].get("overlays", [])
    base_contours = [contours[l][0] for l in base_layers]
    layer_names = base_layers
    if len(base_contours) > 1:
        ground_cover = complete_cover(base_contours, 4)

    for layer in overlay_layers:
        contour = contours[layer][0]
        ground_cover, contour = cut_out_shape(contour, ground_cover)
        layer_names.append(layer)
        ground_cover.append(contour)
    output_file = Path(config.get("output_file", "vectorized.gpkg"))
    write_contours(ground_cover, layer_names, output_dir / output_file)
