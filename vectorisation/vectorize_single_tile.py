from raster_cleaner import clean_mask
from vectorize import get_contours, complete_cover, cut_out_shape
from building_vectorizer import vectorize_building_masks
from vectorize.PolygonSmoother import smooth_multipolygon, simplify_multipolygon

from gaia_io import load_mask, write_mask, write_contours, valided_and_filter_contour

from pathlib import Path

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process some masks.")
    parser.add_argument("mask_tile", help="Path to the raster tile")
    parser.add_argument("output_gpkg", help="Path to the output GeoPackage")

    parser.add_argument(
        "--min-area", type=float, default=5, help="Minimum mask area to keep"
    )

    parser.add_argument("--mask-threshold", type=int, default=64, help="Mask threshold")

    parser.add_argument(
        "--min-poly-area",
        type=float,
        default=10,
        help="The smallest polygon area to keep",
    )
    parser.add_argument(
        "--min-hole", type=float, default=5, help="Minimum hole area to keep"
    )
    parser.add_argument(
        "--shortest-edge", type=float, default=1, help="Shortest edge of a mask"
    )
    parser.add_argument(
        "--sigma", type=float, default=0.2, help="Sigma for Gaussian blur"
    )
    parser.add_argument(
        "--gap-closure", type=float, default=4, help="Gap closure distance"
    )
    parser.add_argument("--simplify", type=float, default=1, help="Simplify tolerance")
    parser.add_argument("--smooth", type=float, default=0, help="Smooth tolerance")
    parser.add_argument(
        "--smooth-method",
        default="chaikin",
        help="Smoothing method (chaikin, paek, bezier, taubin, laplacian)",
    )
    parser.add_argument(
        "--write-intermediate", action="store_true", help="Write intermediate masks"
    )

    parser.add_argument("--building", action="store_true", help="Vectorize buildings")

    args = parser.parse_args()
    mask_path = Path(args.mask_tile)
    if not mask_path.exists():
        print(f"Mask tile {args.mask_tile} not found")
        exit(1)

    mask, transform = load_mask(args.mask_tile)

    mask[mask < args.mask_threshold] = 0

    pixel_size = transform.a
    mask = clean_mask(
        mask,
        args.min_area,
        args.min_hole,
        args.gap_closure,
        pixel_size,
        sigma=args.sigma,
    )
    print(mask.min())
    print(mask.max())
    print(mask.shape)

    if args.write_intermediate:
        write_mask(mask, transform, mask_path.with_suffix(".clean.tif"))

    if args.building:
        contour = contour = vectorize_building_masks(
            mask, transform, args.min_area, args.shortest_edge, True
        )
    else:
        contour = get_contours(mask, args.min_area, transform)
        if args.write_intermediate:
            write_contours(
                contour, "base_contours", mask_path.with_suffix(".contours.gpkg")
            )
        if args.smooth > 0:
            contour = smooth_multipolygon(contour, args.smooth_method, 0, args.smooth)
            if args.write_intermediate:
                write_contours(
                    contour, "smoothed", mask_path.with_suffix(".smoothed.gpkg")
                )
        if args.simplify > 0:
            contour = simplify_multipolygon(contour, args.simplify, "vw")

    contour = valided_and_filter_contour(contour, args.min_poly_area)
    write_contours(contour, "vectorize", args.output_gpkg)
