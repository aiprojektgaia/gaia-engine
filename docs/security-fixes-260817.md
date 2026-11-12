# Security fixes — audit 2026-08-17

Remediation of `vulnerability_audit_260817.json` (OWASP Dependency-Track 4.14.1
/ Trivy). The audit reported **4 vulnerabilities across 3 packages**. Two were
real and are fixed; two were false positives and are documented below.

## Fixed

| File | Package | Was | Now | Advisory |
|---|---|---|---|---|
| `core/image_bitter/requirements.txt` + `gaia-backend/Dockerfile` | GDAL | 3.13.0 (bindings) / libgdal 3.10.1 (image) | 3.13.2 both | GHSA-wphc-7cm7-8mf7 — stack buffer overflow in the netCDF driver, high |
| `segmentation/requirements.txt` | pytorch-lightning | 2.5.0.post0 | 2.6.5 | GHSA-75m9-98v2-hjpm — insecure deserialization in checkpoint loading, high |

### GDAL — the pip pin alone was never the fix

GHSA-wphc-7cm7-8mf7 is a stack buffer overflow in `frmts/netcdf/netcdfsg.cpp` —
**native libgdal C++ code**. The pip pin selects only the Python bindings and
does not patch the shared library. The genuinely vulnerable component was the
`libgdal 3.10.1` in the backend's base image, well inside the advisory's
"3.1.0 through 3.13.0" range. The SBOM reported 3.13.0 because it read the pip
pin rather than the linked library, so the finding understated the problem: the
deployed native library was *older* than the version the scanner named.

Closing it therefore required moving **both**, in lockstep:

| Where | From | To |
|---|---|---|
| `gaia-backend/Dockerfile` base image | `ubuntu-small-3.10.1` | `ubuntu-small-3.13.2` |
| `core/image_bitter/requirements.txt` | `GDAL==3.13.0` | `GDAL==3.13.2` |

The same commit changes `python3.12-dev` to `python3-dev` in the Dockerfile. The
GDAL base images track their Ubuntu release (24.04, and 26.04 on the newest
tags), so the default Python moves with them and a hardcoded minor version stops
resolving.

#### Why bumping only the pin broke production (2026-08-18)

Bumping `requirements.txt` to 3.13.2 while the image still provided libgdal
3.10.1 took the system down. The mechanism is worth recording:

`interface_service.install_requirements()` re-runs
`pip install -r requirements.txt` for **every** interface on **every** container
start, with `check=True`. GDAL on PyPI is sdist-only and its bindings must match
the native library, so the new pin forced a source build that failed.
`install_existing_interface()` caught the error and flagged the interface
uninstalled. The runtime symptom appeared much later as:

```
ValueError: Interface image_bitter is not active or installed
```

then cascaded — `to_bit_image` produced nothing, so the next task found no
finished predecessor steps and killed the run.

`GDAL==3.13.0` had never actually built on that image either. It survived only
because the version was already present in the interface venv, so pip reported
"Requirement already satisfied" and skipped the build. Changing the pin removed
that free pass. **The pin and the base image must always move together.**

#### Required deployment step — delete every interface venv

**Whenever the backend base image changes, all interface venvs must be deleted.**
They live on the host bind-mount (`/opt/gaia/gaia-engine`), so they survive
`docker compose up --build` and silently break the next start.

```bash
rm -rf /opt/gaia/gaia-engine/*/venv /opt/gaia/gaia-engine/core/*/venv
cd /opt/gaia/gaia-backend/docker
docker compose -f linux.docker-compose.yml up --build -d
```

Two independent reasons, both of which bit during the 2026-08-18/19 rollout:

1. **Native library alignment.** `image_bitter`'s venv held GDAL bindings
   compiled against libgdal 3.10.1. Stale bindings and a new native library
   disagree.
2. **Python ABI.** The venvs were created by the old image's system Python 3.12
   and their `bin/python3.12` links against `libpython3.12.so.1.0`. The 3.13.2
   base ships a different default Python, so every stale venv failed with:

   ```
   error while loading shared libraries: libpython3.12.so.1.0:
   cannot open shared object file: No such file or directory
   ```

   Deleting only `image_bitter`'s venv fixed that one interface and left the
   other five broken. The lesson: this is an all-or-nothing migration.

Recreated venvs are built by uv's bundled CPython 3.12.14, which is
self-contained, so the ABI problem does not recur on later restarts of the same
image.

Expect a slow first start: `segmentation` pulls `torch` via
`segmentation-models-pytorch` and `pytorch-lightning` (several GB). A long silent startup is expected,
not a hang. Confirm with:

```bash
docker compose -f linux.docker-compose.yml logs gaia \
  | grep -iE "Installing requirements|Error setting up interface|Finished scanning"
```

`Finished scanning and installing interfaces` with no error lines means the
stack is healthy.

Not affected by the GDAL change itself: `comparison` and `vectorisation` use
`rasterio` and `fiona`, which bundle their own GDAL inside their wheels. They
still needed their venvs deleted for the Python ABI reason above.

#### Why a failed install is more damaging than it looks

`install_existing_interface()` catches any install error and calls
`uninstall_interface()`, which sets **both** `installed = False` *and*
`is_active = False`. `get_by_group_name()` filters on `is_active`, so a failed
interface disappears from `GET /models/segmentation` — and the QGIS client's
"Välj objektyper" selector renders empty, because it draws one checkbox per
model returned. The flag is only restored when a later start installs
successfully. A transient pip or network failure therefore removes object types
from the client UI until the next good boot, with no error shown to the user.

#### Two code issues this exposed

- `install_requirements()` calls `subprocess.run(..., check=True,
  capture_output=True)`, so `CalledProcessError` is raised before the
  `if result.returncode != 0` branch — making
  `raise Exception(f"Error installing requirements: {result.stderr}")`
  **unreachable**. pip's real build error is discarded, leaving only
  "returned non-zero exit status 1". Logging `e.stderr` would have made this
  diagnosable in seconds instead of via traceback archaeology.
- Re-installing every interface's requirements on every start means a transient
  network or build failure silently disables a working interface, with the
  failure surfacing only when a job later tries to use it.

### pytorch-lightning — already mitigated in code

GHSA-75m9-98v2-hjpm concerns `LightningModule.load_from_checkpoint()` calling
`torch.load()` without `weights_only=True`, allowing arbitrary code execution
from a malicious checkpoint. OSV lists no fixed version for the advisory, so the
upgrade alone is not the argument.

This engine was **never** exposed:

- `load_from_checkpoint()` is not called anywhere in the codebase.
- The one checkpoint load, `segmentation/resunet_inferencer.py:43`, already
  passes the safe flag:
  ```python
  ckpt = torch.load(checkpoint, map_location='cpu', weights_only=True)
  ```

The bump to 2.6.5 is still worth taking — OSV reports 2.6.1+ as clean — but the
existing code was the real mitigation. **Keep `weights_only=True`** on any future
checkpoint load, and do not introduce `load_from_checkpoint()`.

## False positives — no action possible or required

| Package | Version | Advisories | Why |
|---|---|---|---|
| fiona | 1.10.1 | GHSA-g4m4-9q4c-mfw6, GHSA-q5fm-55c2-v6j9 | Fixed in `1.10b2` and `1.10b1` respectively. The pinned `1.10.1` is **already past both**, and is also the latest release — there is nothing to upgrade to. The scanner appears to mis-order the beta versions against the release. |

Both advisories concern GDAL/libjpeg vulnerabilities inherited through the GDAL
bundled in Fiona's wheels, and Fiona's own advisory text states the 1.10 wheels
are not vulnerable. `fiona` is left at `1.10.1` in
`vectorisation/requirements.txt` and `vectorisation/pyproject.toml`.

If Dependency-Track keeps reporting these, suppress them there rather than
churning the pin.

## Verification

Every pinned requirement across all five requirement files
(`comparison`, `core/image_bitter`, `core/wms_tiler`, `segmentation`,
`vectorisation`) was checked against OSV: **0 outstanding advisories**.

Tests run: `core/wms_tiler` — 3 passed, 3 failed. The failures are pre-existing
and unrelated to dependencies (see below). `core/image_bitter` tests could not
run in this environment: `file_merger.py` imports `osgeo`, which needs the
system GDAL from OSGeo4W/conda.

## Known issue (not introduced here, not fixed here)

`core/wms_tiler/tests/create_tile_boundaries_test.py` has three failing tests:

```
assert '(0, 0), (5.0, 5.0)' == '(0, 0), (5, 5)'
```

`create_tile_boundaries()` deliberately coerces with `float_size =
float(tile_size)`, so tile bounds are floats, while the tests compare
`str(BoundingBox)` against int-valued expectations. The tests are stale relative
to the code; the code looks correct. `wms_tiler` was not modified by this work —
its only dependency is `requests`, which is unchanged.
