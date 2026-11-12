# Comparison

Compare a binary image to the basemap (geojson-file) and produce a labeled image with the comparison result. The result image is a grayscale image where the graylevels correspond to a label.

## Usage (Example)
To run the comparison, specify the path to the image file, the path to the result folder and the name of the class that should be compared (supported classes are 'buildings' and 'roads')
```shell
python main.py data/buildings/65715_1635.tif data/buildings/65715_1635.json results/buildings buildings
python main.py data/roads/65715_1640.tif data/roads/65715_1640.json results/roads roads
```

## Output
The labels in the output image have the following meaning:\
0 - background (no object in neither basemap or orthophoto)\
1 - same building\
2 - added building (building in orthophoto but not in basemap)\
3 - removed building (building in basemap but not in orthophoto)\
4 - building partly extended\
5 - building partly removed\
6 - unknown (the algorithm detected that the shape has changed, but does not know how)\
10 - new road (road in orthophoto but not in basemap)\
100 - building is not fully visible because it is at the edge of the tile

## Classification Rules

The input segmentation image is first binarized using a probability threshold (default 128/255 ≈ 50% confidence). Pixels above the threshold are treated as detected buildings; pixels below are background.

The comparison then runs in two passes.

**Pass 1 — connected-component comparison**\
The basemap polygons are rasterized and combined with the binarized segmentation via a union (bitwise OR). Connected components of the union are labeled and each component is classified independently:

- **100 (edge):** the component's bounding box touches any border of the image tile — the building may be partially cut off.
- **2 (added):** basemap pixels in the component are less than 10% of the segmentation pixels — the building exists in the segmentation but not in the basemap.
- **3 (removed):** segmentation pixels in the component are less than 10% of the basemap pixels — the building exists in the basemap but not in the segmentation.
- **1 (same):** the contour shapes of basemap and segmentation match within the shape threshold (default 0.1 using Hu-moment comparison).
- **5 (partly removed):** the segmentation pixels are a strict subset of the basemap pixels in the component (the building shrank).
- **4 (partly extended):** the basemap pixels are a strict subset of the segmentation pixels (the building grew).
- **5 / 4 (area ratio):** when shapes are similar, the area ratio determines direction — if seg/basemap ≤ 0.90 → partly removed; if basemap/seg ≤ 0.90 → partly extended.
- **6 (unknown):** shape has changed but the algorithm cannot determine how.

The 10% noise tolerance and 90% area ratio are configurable via `ratio` in `parameters.json`.

**Pass 2 — per-polygon removed check**\
Because adjacent buildings can merge into a single connected component in the union, Pass 1 may miss individual removed buildings inside a larger cluster. Pass 2 iterates over each GeoJSON polygon separately: if the segmentation coverage within a polygon's footprint is below 10% of the polygon area, that polygon is labeled **3 (removed)**, overwriting the Pass 1 result for those pixels.
