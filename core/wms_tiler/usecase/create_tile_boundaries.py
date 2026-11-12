import math

from models.LayerInfo import BoundingBox

def create_tile_boundaries(bbox: BoundingBox, tile_size: int) -> list[BoundingBox]:
    """
    Create a list of bounding boxes for tiles of the given size that cover the input bounding box.
    """
    tile_boundaries = []
    min_x, min_y, max_x, max_y = bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y

    print(f"min_x: {min_x}, min_y: {min_y}, max_x: {max_x}, max_y: {max_y} -> tile_size: {tile_size}")
    #print("types:", type(min_x), type(min_y), type(max_x), type(max_y))
    float_size = float(tile_size)

    # Index-based so every iteration is guaranteed to make progress.
    columns = math.ceil((max_x - min_x) / float_size)
    rows = math.ceil((max_y - min_y) / float_size)
    for i in range(columns):
        # first row/column keep the caller's value unchanged
        x = min_x if i == 0 else min_x + i * float_size
        for j in range(rows):
            y = min_y if j == 0 else min_y + j * float_size
            tile_boundaries.append(BoundingBox(x, y, x + float_size, y + float_size))

    return tile_boundaries

def apply_overlap(tile_boundaries: list[BoundingBox], tile_size: int, overlap_percentage: int) -> list[BoundingBox]:
    """
    Increase the size of the bounding boxes in the list by the given overlap.
    """
    overlap = float(tile_size) * (float(overlap_percentage) / 100.0)
    print(f"overlap added in meters is: {overlap}")
    return [BoundingBox(bbox.min_x - overlap, bbox.min_y - overlap, bbox.max_x + overlap, bbox.max_y + overlap) for bbox in tile_boundaries]

def get_tile_size_in_meters(mpp, tile_size_in_pixels):
    print(f"mpp: {mpp}, tile_size_in_pixels: {tile_size_in_pixels} => {mpp * tile_size_in_pixels}")
    return mpp * tile_size_in_pixels

def get_unpadded_tile_size_in_meters(tile_size_in_meters, overlap_percentage):
    print(f"tile_size_in_meters: {tile_size_in_meters}, overlap_percentage: {overlap_percentage} => {tile_size_in_meters * 100 / (overlap_percentage + 100)}")
    return tile_size_in_meters * 100 / (overlap_percentage + 100)


#size - 110
# x   - 100
#
# x = 100*size/110