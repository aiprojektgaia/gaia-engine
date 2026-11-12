# Models

Segmentation models, where they live, and how to add one.

## Shipped models

Checkpoints are **not** in the repository — they are large binaries. Obtain them
from [Huggingface](https://huggingface.co/aiprojektgaia) and place them in `segmentation/models/`:

| Class | File | Architecture | Training resolution |
|---|---|---|---|
| `buildings` | `buildings_50e.ckpt` | ResUNet | 0.05 m/px |
| `roads` | `roads_50e.ckpt` | ResUNet | 0.05 m/px |

Without them the interfaces still install, but every run fails at the
segmentation stage.

## Configuration

`segmentation/parameters.json` maps a class to a model:

```json
{
  "data folder": "data",
  "result folder": {
    "buildings": "results/buildings",
    "roads": "results/roads"
  },
  "models": {
    "buildings": {
      "model type": "resunet",
      "model name": "./models/buildings_50e.ckpt",
      "parameters": {
        "resolution": 0.05,
        "sha256": "dedae152836ce06ba6a4dd9a70cfd45f18e97e00810f17bdf0326b80885de8d5"
      }
    }
  }
}
```

| Key | Meaning |
|---|---|
| `model type` | Selects the inferencer. `resunet` is the only one shipped. |
| `model name` | Path to the checkpoint, relative to the module directory |
| `parameters` | Passed to the inferencer constructor. Unknown keys raise. |

`sha256` is **required**. The checkpoint is hashed before it is parsed, and a
model whose file does not match - or that has no digest configured - is refused.
The shipped `parameters.json` pins the digests published on Hugging Face:

| File | SHA-256 |
|---|---|
| `buildings_50e.ckpt` | `dedae152836ce06ba6a4dd9a70cfd45f18e97e00810f17bdf0326b80885de8d5` |
| `roads_50e.ckpt` | `74186af978bd7bf75042f30011aec4e1cae514ceb60cc81c095da08d0a2f2ad5` |

Checkpoints above `GAIA_MAX_CHECKPOINT_BYTES` (default 1 GiB) are refused, and
the stored hyperparameters must match a strict schema (FPN/U-Net-family
architecture, 3 input channels, 1 output class) before a model is built.

`parameters` is validated: `getInferenceModel()` rejects any keyword not already
present in the configured parameters, so a typo fails loudly instead of being
ignored.

## Resolution

**Resolution is reconciled at inference time, not assumed.** The
checkpoints declare `resolution: 0.05` m/px while the tiler defaults to
`mpp: 0.08`. `ResUNetInferencer` handles this explicitly — it rescales each tile
from its own resolution to the model target and crops to a multiple of 32 pixels
(the FPN decoder requires it), then resizes the prediction back to the input
size. So the two values are not in conflict.

What it does mean is that production tiles are **upsampled** 0.08 -> 0.05, and
upsampling cannot recover detail the imagery never captured. Imagery natively
near 0.05 m/px should be expected to perform better.

`resolution` is a per-model parameter in `parameters.json`, so a model trained
at a different GSD only needs its own value set correctly — the rescaling
follows automatically.

## Output format

A segmentation model emits a **greyscale likelihood raster**, not a binary mask:
each pixel is 0–255, expressing how strongly the model believes that pixel
belongs to the class.

Thresholding happens later, in `core/image_bitter`, using the operator's
confidence level. Keep this split — it is what lets a run be re-thresholded
without re-running inference.

## Adding a model for an existing class

1. Put the checkpoint in `segmentation/models/`.
2. Point `model name` at it in `parameters.json`, set its `resolution`, and add
   its `sha256` (`sha256sum model.ckpt`). Only add digests of checkpoints you
   trained yourself or obtained from a source you trust.
3. Run the module by hand and inspect the output raster before wiring it in.

## Adding a new object class

A class needs **both** a classification and a vectorisation half, agreeing on the
`classname` string — that string is the only link between them.

1. **Model** — checkpoint in `segmentation/models/`, entry in `parameters.json`
   under `models` and `result folder`.
2. **Classification interface** — add an entry to `segmentation/model.json` with
   `"group": "Classification"` and `"classname": "<your class>"`. The `name`
   appears in the QGIS object-type selector.
3. **Vectorisation interface** — add an entry to `vectorisation/model.json` with
   `"group": "Vectorization"` and the **same** `classname`.
4. **Vectorisation tuning** — add per-class properties (`min_area`,
   `smallest_hole`, `shortest_edge`, `gap_closure`, smoothing, simplification).
   Start from an existing class with similar geometry: `buildings` for compact
   angular shapes, `roads` for long thin ones, `vegetation` for irregular
   organic ones.
5. Restart the backend and confirm the class appears in
   `GET /models/segmentation`.

Skipping step 3 produces a run that segments successfully and then fails at
vectorisation, because no vectoriser matches the class.

## Adding a new architecture

1. Implement an inferencer with the same interface as `ResUNetInferencer`
   (see `inferencer.py` for the base).
2. Register it in `segmentation/inferencer_factory.py`:

   ```python
   inferencers = {'resunet': ResUNetInferencer,
                  'yourtype': YourInferencer}
   ```

3. Reference it as `model type` in `parameters.json`.

### Loading checkpoints safely

Always:

```python
ckpt = torch.load(checkpoint, map_location="cpu", weights_only=True)
```

`weights_only=True` is a security control, not a performance flag — without it a
crafted checkpoint executes arbitrary code on load. **Do not use
`LightningModule.load_from_checkpoint()`**, which does not set it. See
[DEPENDENCIES.md](DEPENDENCIES.md).

Treat checkpoints as untrusted input whenever they did not come from your own
training run.

## Licence note

All current dependencies are permissively licensed. Check the licence before
adding an inferencer that pulls in a new framework — `ultralytics` was removed
from this engine precisely because its AGPL-3.0 terms would propagate to the
whole project. See [DEPENDENCIES.md](DEPENDENCIES.md).
