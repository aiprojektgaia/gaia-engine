# Engine architecture

How the engine modules are organised internally. For the system-level view — the
pipeline, the interface contract, how the backend invokes all this — see
[gaia-backend/docs/ARCHITECTURE.md](https://github.com/aiprojektgaia/gaia-backend/blob/main/docs/ARCHITECTURE.md).

## Shape of the engine

Every module is a **standalone CLI program**, not a library and not a service.
The backend launches it as a subprocess, waits for nothing, and is notified by
an HTTP callback when the process finishes.

Consequences worth designing around:

- **Modules share no runtime state.** Everything is passed on the command line or
  read from disk. Two modules communicate only through files.
- **A module owns one unit of work.** One tile, one image, one class — not a
  folder or a batch. The backend creates one step per unit.
- **Modules must report their own completion.** A module that exits without
  calling back leaves its step `RUNNING` forever, stalling the whole server.
- **Dependencies are per-module and conflicting.** `torch`, GDAL and
  `fiona`/`shapely` cannot share one environment, which is why each module has
  its own `requirements.txt` and its own `venv/`.

```
core/wms_tiler   →  segmentation  →  core/image_bitter  →  vectorisation
   tiles .tif       masks .tif        filtered .tif         .gpkg
```

`comparison` sits outside this chain and is invoked for the
`CompareToBaseImage` run type.

## Data flow

Everything moves through GeoTIFF files carrying their own georeference, until
the final GeoPackage.

| Stage | Input | Output |
|---|---|---|
| `wms_tiler` | bbox + WMS URL | Overlapping GeoTIFF tiles |
| `segmentation` | One tile | Greyscale raster: pixel value = likelihood (0–255) |
| `image_bitter` | One mask | Same raster with sub-threshold pixels zeroed |
| `vectorisation` | One mask | GeoPackage of polygons |
| `comparison` | Mask + base map | Difference geometry |

Because segmentation emits a **likelihood** raster rather than a binary mask,
the confidence threshold is applied later, in `image_bitter`. That is what lets
the operator choose a confidence level per run without re-running the model.

## Tiling

The tiler cuts the requested bounding box into square tiles with a percentage
overlap:

```
tile_size_metres     = mpp × tile_size_pixels          # 0.08 × 1024 = 81.92 m
unpadded_tile_metres = tile_size_metres × 100 / (overlap + 100)
overlap_metres       = tile_size_metres × (overlap / 100)
```

Tiles are laid out at `unpadded` spacing, then grown by `overlap_metres` on
every side. The overlap exists so a building or road crossing a tile boundary is
seen whole by the model; the surplus is discarded when tiles are merged.

Tiling is what makes the run size manageable — a model sees a fixed 1024×1024
input regardless of how large an area the operator selected. It is also what
makes runs slow: work grows with the *area* of the bounding box.

`vectorisation/large_image_tiler/` performs the same trick again for rasters too
large to vectorise in one pass.

## Segmentation

`engine_runner.py` is the entry point. `inferencer_factory.getInferenceModel()`
reads `parameters.json`, looks up the model type for the requested `classname`,
and instantiates the matching inferencer:

| `model type` | Class | Notes |
|---|---|---|
| `resunet` | `ResUNetInferencer` | Both shipped checkpoints. PyTorch Lightning. |

Despite the `resunet` key, the architecture is not fixed by the loader: it passes
`arch` from the checkpoint hyperparameters into `smp.create_model()`. Both
shipped checkpoints are FPN with a ResNet34 encoder.

Adding an architecture means adding an inferencer class and registering it in
the `inferencers` dict. See [MODELS.md](MODELS.md).

> Checkpoints are loaded with `torch.load(..., weights_only=True)`. **Keep that
> flag.** Without it a malicious checkpoint can execute arbitrary code, and
> `LightningModule.load_from_checkpoint()` — which does not set it — must not be
> used.

## Vectorisation

The most structured module. Raster in, polygons out, in stages:

| Package | Responsibility |
|---|---|
| `raster_cleaner/` | Morphological tidying before tracing — closes gaps, drops speckle |
| `large_image_tiler/` | Splits rasters too large to process in one pass |
| `vectorize/` | Raster-to-polygon tracing, polygon covering |
| `building_vectorizer/` | Building-specific: `growing_rectangles` favours straight edges and right angles |
| `layer_types/` | Per-class behaviour — `buildings.py` vs `generalized_type.py` |
| `gaia_io/` | Reading and writing geospatial formats |

Buildings get a dedicated path because a generic raster tracer produces ragged
outlines where a building should have straight walls and square corners. Roads
and vegetation use the generalized type with smoothing instead.

Per-class tuning — `min_area`, `smallest_hole`, `shortest_edge`, `gap_closure`,
smoothing and simplification — is configuration, not code. See
`config_testcase.json` for the shape and
[the backend architecture doc](https://github.com/aiprojektgaia/gaia-backend/blob/main/docs/ARCHITECTURE.md#imagery-and-tiling-parameters)
for the values in use.

## Comparison

Compares fresh segmentation output against an existing base map to find what
changed. `comparer_factory.getComparer()` resolves a comparer per class from
`parameters.json`, in two layers:

- **Tile comparers** — `BuildingTileComparer`, `RoadTileComparer`. Operate on
  raster tiles.
- **Segment comparers** — optional second pass on individual segments.

`ComparerV1` is the current top-level strategy. Building comparison detects
per-polygon removal; roads use a different threshold model, which is why they
are separate classes rather than one parameterised comparer.

## Conventions when adding a module

1. One directory, containing `model.json`, `requirements.txt` and `main.py`
   (`main.py` must exist even if `module_file_name` names something else).
2. Accept `--image-path`, `--output-path`, `--callback-url`; add `--classname`
   for classification or vectorisation.
3. Do one unit of work per invocation.
4. Write results to `--output-path` and nowhere else — the next stage reads that
   directory.
5. POST to `--callback-url` on success **and** on failure. Never exit silently.
6. Pin dependencies exactly, and check [DEPENDENCIES.md](DEPENDENCIES.md) before
   pinning anything with a native component.
