import rasterio
import subprocess
import collections.abc
import tempfile
from math import ceil
from pathlib import Path
from rasterio.windows import Window
import numpy as np
# from shapely import box

# def get_tile_bounds(tile, transform):
#     """Get the bounds of a tile in the coordinate system of the input image"""
#     x0 = transform.c
#     y0 = transform.f
#     x1 = transform.c + transform.a * tile.shape[2] + transform.b * tile.shape[2]
#     y1 = transform.f + transform.c * tile.shape[1] + transform.d * tile.shape[1]
#     minx = min(x0, x1)
#     maxx = max(x0, x1)
#     miny = min(y0, y1)
#     maxy = max(y0, y1)
#     return box(minx, miny, maxx, maxy)


def get_input_img_path(in_img, img_suffix="tif"):
    if isinstance(in_img, collections.abc.Sequence) and not isinstance(in_img, str):
        # we (probably) have a list of paths
        for img_path in in_img:
            in_img_list = []
            if not Path(img_path).is_file():
                raise ValueError(f"Invalid input image: {img_path}")
            else:
                in_img_list.append(Path(img_path).absolute())
    else:
        # we (probably) have a single path
        in_img = Path(in_img).absolute()
        if in_img.is_file():
            in_img_list = [in_img]
        elif in_img.is_dir():
            in_img_list = list(in_img.glob("**/*." + img_suffix))
    if len(in_img_list) == 0:
        raise ValueError("No input images found")
    elif len(in_img_list) > 1:
        in_img_path = create_vrt(in_img_list)  # create vrt
    else:
        in_img_path = in_img_list[0]

    return in_img_path


def create_vrt(in_img_list, out_vrt=None):
    if out_vrt is None:
        tmp_out_vrt = tempfile.NamedTemporaryFile(suffix=".vrt", delete=False)
        out_vrt = tmp_out_vrt.name
        print(f"Creating temporary vrt: {out_vrt}")
        tmp_out_vrt.close()
    try:
        cmd = ["gdalbuildvrt", "-overwrite", out_vrt] + [str(i) for i in in_img_list]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create vrt {e}") from e
    return out_vrt


class TileGenerator:
    def __init__(self, in_img, tile_size, overlap=0, no_alpha=False, pad=False, img_suffix="tif"):
        self.input_img_path = get_input_img_path(in_img, img_suffix)
        self.tile_width, self.tile_height = tile_size
        self.overlap = overlap
        self.no_alpha = no_alpha
        self.crs = None
        self.pad = pad
        with rasterio.open(self.input_img_path) as dataset:
            self.n_tiles_x = ceil(
                (dataset.width - self.overlap) / (self.tile_width)
            )
            self.n_tiles_y = ceil(
                (dataset.height - self.overlap) / (self.tile_height)
            )
            self.crs = dataset.crs
        self.n_tiles = self.n_tiles_x * self.n_tiles_y

    def __iter__(self):
        with rasterio.open(self.input_img_path) as dataset:
            # Calculate the number of tiles in each dimension
            n_tiles_x = ceil(
                (dataset.width - self.overlap) / (self.tile_width)
            )
            n_tiles_y = ceil(
                (dataset.height - self.overlap) / (self.tile_height)
            )

            for y in range(n_tiles_y):
                for x in range(n_tiles_x):
                    window = Window(
                        max((x * self.tile_width) - self.overlap, 0),
                        max((y * self.tile_height) - self.overlap, 0),
                        self.tile_width,
                        self.tile_height,
                    )
                    transform = dataset.window_transform(window)
                    
                    if self.no_alpha:
                        tile = dataset.read((1, 2, 3), window=window)
                    else:
                        tile = dataset.read(window=window)
                    if self.pad:
                        pad_x = self.tile_width - tile.shape[2]
                        pad_y = self.tile_height - tile.shape[1]
                        if pad_x > 0 or pad_y > 0:
                            tile = np.pad(tile, ((0, 0), (0, pad_y), (0, pad_x)), mode="constant")
                    yield tile, transform, (x, y)

    def __len__(self):
        return self.n_tiles


class RasterTileExtractor:
    def __init__(self, in_img, img_suffix="tif"):
        self.input_img_path = get_input_img_path(in_img, img_suffix)
        self.ds = rasterio.open(self.input_img_path)

    def get_tile(self, xmin, ymin, xmax, ymax):
        window = Window(xmin, ymin, xmax - xmin, ymax - ymin)
        transform = self.ds.window_transform(window)
        tile = self.ds.read(window=window)
        return tile, transform

    def __del__(self):
        self.ds.close()

if __name__ == '__main__':
    import argparse
    try: 
        from tqdm import tqdm
    except ImportError:
        tqdm = lambda x: x
    

    parser = argparse.ArgumentParser(description="Generate tiles from an image")
    
    parser.add_argument("--height","-H", type=int, required=True, help="Height of the tiles")
    parser.add_argument("--width","-W", type=int, required=True, help="Width of the tiles")
    parser.add_argument("--overlap","-l", type=int, default=0, help="Overlap between tiles")
    parser.add_argument("--no_alpha", action="store_true", help="Don't include alpha channel in output")

    parser.add_argument("input_img", help="Path to the input image")
    parser.add_argument("output_dir", help="Path to the output directory")



    args = parser.parse_args()
    in_img = Path(args.input_img)
    if "*" in in_img.name:
        in_img_root = in_img.parent
        in_img_list = list(in_img_root.glob(in_img.name))
        if len(in_img_list) == 0:
            raise ValueError(f"No images found matching {in_img}")
    else:
        if not in_img.is_file():
            raise ValueError(f"Invalid input image: {args.input_img}")
        in_img_list = [in_img]
    
    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True, parents=True)

    for img in in_img_list:
        
        tile_generator = TileGenerator(img, (args.width, args.height), args.overlap, args.no_alpha, pad=True)
        num_tiles = len(tile_generator)
        print(f"Generating {num_tiles} tiles for {img}")
        for tile, transform, (x, y) in tqdm(tile_generator, total= num_tiles):
            if tile.shape[1] == 0 or tile.shape[2] == 0:
                continue
            out_path = out_dir / f"{img.stem}_tile_{x}_{y}.png"
            with rasterio.open(out_path, "w", driver="png", width=tile.shape[2], height=tile.shape[1], count=tile.shape[0], dtype=tile.dtype, transform=transform) as dst:
                dst.write(tile)




