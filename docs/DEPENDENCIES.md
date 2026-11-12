# Dependencies

Why the engine pins the way it does, and the two rules that will break a
deployment if ignored.

## One environment per module

Each module has its own `requirements.txt` and its own `venv/`. This is not
tidiness — the dependency sets genuinely conflict:

| Module | Heavy dependencies |
|---|---|
| `segmentation` | `torch`, `segmentation-models-pytorch`, `pytorch-lightning`, `opencv-python` |
| `vectorisation` | `fiona`, `shapely`, `scikit-image`, `opencv-python`, `simplification` |
| `core/image_bitter` | `GDAL`, `rasterio`, `numpy` |
| `core/wms_tiler` | `requests` |
| `comparison` | `geopandas`, `rasterio`, `opencv-contrib-python` |

`torch` alone is several GB. Installing all of these together would produce an
unresolvable environment and a very slow container.

The backend creates and maintains these environments automatically. It runs
`pip install -r requirements.txt` for every module **on every start**, not just
the first — so a changed pin takes effect on the next restart with no rebuild,
and a broken pin disables that module until fixed.

## Rule 1 — GDAL must match the Docker base image

`GDAL` on PyPI ships as an **sdist only**. There is no wheel: pip compiles it,
and the Python bindings must match the native `libgdal` they build against.

That native library comes from the backend's Docker base image:

```dockerfile
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.13.2   # gaia-backend/Dockerfile
```

```
GDAL==3.13.2                                   # core/image_bitter/requirements.txt
```

**These two move together or not at all.** Changing the pin alone forces a
source build against a mismatched library, which fails; the interface is then
flagged inactive and image processing stops. Changing the base image alone
leaves stale bindings compiled against the previous version.

This is not hypothetical — it took production down on 2026-08-18. The full
post-mortem is in [security-fixes-260817.md](security-fixes-260817.md).

A pin can also appear to work while being wrong: if the version is already
installed in the venv, pip reports "Requirement already satisfied" and never
attempts the build. The mismatch only surfaces when the venv is recreated.

### Rule 1a — changing the base image invalidates every venv

Interface venvs live on a host bind-mount and survive image rebuilds, but they
link against the interpreter of the image that created them. A new base image
with a different Python produces:

```
error while loading shared libraries: libpython3.12.so.1.0
```

on **every** module. All venvs must be deleted together:

```bash
rm -rf /opt/gaia/gaia-engine/*/venv /opt/gaia/gaia-engine/core/*/venv
```

## Rule 2 — pins are exact on purpose

Most requirements use `==`. Engine modules run unattended inside a pipeline
where a silent behaviour change produces subtly wrong geometry rather than an
error — a different `shapely` simplification or `opencv` morphology can shift
every polygon slightly without failing.

`numpy>=2.1` and a few others are ranges where the module genuinely tolerates
them. Prefer `==` for anything touching geometry, imagery or model inference.

Note that `rasterio` and `fiona` bundle **their own** GDAL inside their wheels.
They are independent of the base image, which is why they were unaffected by the
GDAL incident.

## Third-party licences

Licensing is a distribution constraint, not just paperwork:

| Package | Licence | Consequence |
|---|---|---|
| `pytorch-lightning` | Apache-2.0 | Permissive |
| `segmentation-models-pytorch` | MIT | Permissive |
| `fiona`, `rasterio` | BSD | Permissive |
| `opencv-python` | Apache-2.0 | Permissive |

Every remaining dependency is permissively licensed, so the engine itself can
be distributed under a permissive licence.

`ultralytics` (**AGPL-3.0**) was removed in 2026-08 together with
`segmentation/yolo_inferencer.py`. Neither shipped checkpoint used it — both are
FPN/ResNet34 loaded through `ResUNetInferencer` — so removing it cost no
functionality and lifted the copyleft constraint.

**Do not reintroduce `ultralytics`** without a deliberate licence decision: its
AGPL-3.0 terms would propagate to this engine and, through the network clause,
to anyone offering it as a service.

## Security

Checkpoint loading must use `weights_only=True`:

```python
ckpt = torch.load(checkpoint, map_location="cpu", weights_only=True)
```

Without it, `torch.load` unpickles arbitrary Python objects and a malicious
checkpoint achieves code execution. **Do not use
`LightningModule.load_from_checkpoint()`** — it does not set the flag, and the
corresponding advisory (GHSA-75m9-98v2-hjpm) has no fixed version. The code-level
flag is the mitigation.

Dependencies were scanned, findings and their dispositions — including confirmed false positives — are
recorded in [security-fixes-260817.md](security-fixes-260817.md).

## Upgrading a dependency

1. Change the pin in the module's `requirements.txt`.
2. If it has a native component, check whether the base image provides it.
3. Delete that module's `venv/` so the change is genuinely exercised, rather
   than skipped as "already satisfied".
4. Restart the backend and confirm no `Error setting up interface` line appears.
5. Run the module by hand on a known input and compare output — pipeline stages
   fail quietly far more often than they crash.
