**This repository is not maintained**

This code is provided as-is under its licence, with no maintainer. Vulnerability
reports will not be received, triaged or fixed. Anyone who deploys or forks this
code is solely responsible for its security, including keeping dependencies
patched.

# gaia-engine

The processing half of GAIA: fetches aerial imagery, runs semantic segmentation
over it, and converts the result into vector geometry.

The engine is **not** a service. Each module is a standalone command-line program
that `gaia-backend` launches as a subprocess in its own virtual environment. It
can also be run by hand, which is how you develop and debug it.

## Where this fits

GAIA is three repositories. The system-level description lives in the backend:

| Repository | Role |
|---|---|
| **gaia-backend** | REST API, database, scheduling. Launches this engine. |
| **gaia-engine** (this one) | Tiling, segmentation, vectorisation, comparison. |
| **gaia-client** | QGIS plugin. The user interface. |

See **[gaia-backend/docs/ARCHITECTURE.md](https://github.com/aiprojektgaia/gaia-backend/blob/main/docs/ARCHITECTURE.md)**
for the pipeline, the interface contract and the tiling parameters.

## Modules

Each directory with a `model.json` is an **interface** the backend can discover
and run.

| Module | Group | Does |
|---|---|---|
| `core/wms_tiler` | `Internal` | Fetches imagery from a WMS and cuts it into overlapping tiles |
| `segmentation` | `Classification` | Runs a segmentation model per tile, producing a greyscale likelihood raster |
| `core/image_bitter` | `Internal` | Applies the confidence threshold — pixels below it are zeroed |
| `vectorisation` | `Vectorization` | Converts a raster mask into polygons and writes a GeoPackage |
| `comparison` | — | Compares segmentation output against an existing base map |

Pipeline order: **tile → segment → merge → vectorise → merge → confidence.**

## Running a module directly

Every module takes `--image-path`, `--output-path` and `--callback-url`.
`--callback-url` may be omitted when running locally; the backend always
supplies it.

### Tiling

```bash
cd core/wms_tiler
python main.py \
  --wms-server-url http://localhost:9600/geoserver/wms \
  --layer-name my_ortho \
  --bbox "374000,6165000,374500,6164500" \
  --epsg EPSG:3006 \
  --output-path /tmp/tiles \
  --tile-size-pixels 1024 --overlap 10 --mpp 0.08
```

`--bbox` is `min_x, max_y, max_x, min_y` — **not** the usual GIS ordering.
Defaults: `tile-size-pixels 1024`, `overlap 10` (percent), `mpp 0.08`
(metres/pixel), `image-format geotiff`.

### Segmentation

```bash
cd segmentation
python engine_runner.py --classname buildings \
  --image-path /tmp/tiles/tile_0.tif \
  --output-path /tmp/masks
```

`--classname` is one of `buildings`, `roads`. Output is a greyscale raster where
each pixel value is the likelihood it belongs to the class.

### Confidence threshold

```bash
cd core/image_bitter
python main.py --image-path /tmp/masks/tile_0.tif \
  --output-path /tmp/filtered --confidence-level 75
```

`--confidence-level` is a percentage; values below it are zeroed.
`--max-confidence-value` defaults to `255`.

### Vectorisation

```bash
cd vectorisation
python engine_runner.py --classname buildings \
  --image-path /tmp/filtered/tile_0.tif \
  --output-path /tmp/vectors
```

### Comparison

Positional arguments, unlike the others:

```bash
cd comparison
python main.py <image> <basemap.geojson> <output_folder> <classname>
```

## Development setup

Each module has its own dependencies, and they conflict — `torch` for
segmentation, GDAL for imagery, `fiona`/`shapely` for vectors. Never install
them into one shared environment. One virtual environment per module:

```bash
cd segmentation
python -m venv venv
venv/bin/pip install -r requirements.txt
```

This mirrors what the backend does automatically: it creates `<module>/venv` and
reinstalls `requirements.txt` on **every** start.

> Version pins here are exact on purpose. `GDAL` in particular must match the
> native `libgdal` in the backend Docker image — changing one without the other
> breaks image processing at runtime. See [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md).

## Models

Segmentation checkpoints are not in the repository — they are large binaries.
Place them in `segmentation/models/` to match `segmentation/parameters.json`:

| Class | File | Architecture | Resolution |
|---|---|---|---|
| `buildings` | `buildings_50e.ckpt` | ResUNet | 0.05 m/px |
| `roads` | `roads_50e.ckpt` | ResUNet | 0.05 m/px |

See [docs/MODELS.md](docs/MODELS.md) for adding a model or a new object class.

## Documentation

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module boundaries, data flow, tiling strategy |
| [docs/MODELS.md](docs/MODELS.md) | Model formats, checkpoints, adding a class |
| [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) | Why pins are exact, GDAL coupling, per-module environments |
| [docs/security-fixes-260817.md](docs/security-fixes-260817.md) | Vulnerability audit record |
| [gaia-backend/docs/INTERFACES.md](https://github.com/aiprojektgaia/gaia-backend/blob/main/docs/INTERFACES.md) | The `model.json` contract |

## License

Copyright 2023-2026 The GAIA project contributors (see [AUTHORS.md](AUTHORS.md))

Licensed under the **Apache License, Version 2.0** ([LICENSE](LICENSE)).

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied.

> All dependencies are permissively licensed. `ultralytics` (AGPL-3.0) was
> removed in 2026-08; do not reintroduce it without a licence decision, as its
> AGPL terms would propagate to the whole engine and are incompatible with
> Apache-2.0 distribution.
