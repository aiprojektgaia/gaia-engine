from pathlib import Path

from building_vectorizer import vectorize_building_masks
from helpers.read_configuration_file import get_config, get_layer_properties
from raster_cleaner import clean_mask
from gaia_io import load_mask, write_contours
from vectorize.PolygonSmoother import smooth_multipolygon, simplify_multipolygon


def start_process(image_path: Path, output_path: Path):
    layer_type_name = "buildings"

    file_path = image_path
    file_name = file_path.name
    output_file_name = file_name.replace(".tif", ".gpkg")

    mask, transform = load_mask(file_path)
    print(f"transform info: {transform}")
    pixel_size = transform.a

    config = get_config("config_testcase.json")
    layer_props = get_layer_properties(config, layer_type_name)

    mask = clean_mask(mask, layer_props.min_area, layer_props.smallest_hole,
                      layer_props.gap_closure, pixel_size, sigma=layer_props.sigma
    )

    apply_smoothing = layer_props.apply_smoothing()
    contour = vectorize_building_masks(
        mask, transform, layer_props.min_area, layer_props.shortest_edge, apply_smoothing
    )

    if apply_smoothing and layer_props.smoothing_parameter > 0:
        contour = smooth_multipolygon(
            contour, layer_props.smoothing, layer_props.subdivide, layer_props.smoothing_parameter
        )

    if layer_props.simplify and layer_props.simplify_tolerance > 0:
        # contour = contour.simplify(layer_props.simplify_tolerance)
        contour = simplify_multipolygon(contour, layer_props.simplify_tolerance, layer_props.simplify)

    write_contours([contour], [layer_type_name], output_path / output_file_name)

    return output_file_name
