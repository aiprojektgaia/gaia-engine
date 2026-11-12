# Segmentation

Runs a semantic segmentation model over a raster tile and produces a greyscale
image where each pixel value expresses the likelihood that the pixel belongs to
the requested class.

Output is **not** a binary mask. Thresholding happens later, in
`core/image_bitter`, using the confidence level the operator chose for the run.
That separation is what allows a run to be re-thresholded without re-running
inference.

## Usage

The entry point used by the backend:

```bash
python engine_runner.py \
  --classname buildings \
  --image-path  /path/to/tile.tif \
  --output-path /path/to/results \
  --callback-url http://backend:8000/run_result/<step-id>
```

| Argument | Required | Meaning |
|---|---|---|
| `--classname` | yes | `buildings` or `roads` — selects the model |
| `--image-path` | yes | A single input tile |
| `--output-path` | yes | Folder for the resulting raster |
| `--callback-url` | by the backend | Omit when running locally |

One invocation processes **one tile**. The backend creates one step per tile per
class.

There is also a positional form for quick local runs:

```bash
python main.py data/65715_1635.tif results/buildings buildings
```

## Models

`parameters.json` maps each class to a checkpoint and an architecture:

| Class | Checkpoint | Architecture | Resolution |
|---|---|---|---|
| `buildings` | `models/buildings_50e.ckpt` | ResUNet | 0.05 m/px |
| `roads` | `models/roads_50e.ckpt` | ResUNet | 0.05 m/px |

Checkpoints are not in the repository — place them in `models/` before running.

`inferencer_factory.py` resolves `model type` to an implementation; `resunet` →
`ResUNetInferencer` is the only one shipped. The loader takes `arch` from the
checkpoint, so it is not limited to one architecture. Adding a model, class or
architecture is covered in [docs/MODELS.md](../docs/MODELS.md).

> **Resolution.** The checkpoints declare 0.05 m/px and the tiler defaults to
> `mpp 0.08`. `ResUNetInferencer` rescales each tile to the model target and
> crops to a multiple of 32 pixels, so these do not conflict — but production
> tiles are upsampled, and upsampling adds no real detail.

## Setup

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt
```

This pulls `torch` via `segmentation-models-pytorch` and `pytorch-lightning` —
several GB, and the slowest environment in the engine to build.

## Security

Checkpoints are loaded with `weights_only=True`:

```python
ckpt = torch.load(checkpoint, map_location="cpu", weights_only=True)
```

Keep it. Without the flag a crafted checkpoint executes arbitrary code on load,
and `LightningModule.load_from_checkpoint()` — which does not set it — must not
be used.
