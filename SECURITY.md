# Security policy

## Reporting a vulnerability

**This repository is not maintained**

This code is provided as-is under its licence, with no maintainer. Vulnerability
reports will not be received, triaged or fixed. Anyone who deploys or forks this
code is solely responsible for its security, including keeping dependencies
patched.

## Scope

This repository contains the processing modules. They run as
subprocesses launched by `gaia-backend`, on the server, with the permissions of
the backend process.

The most security-relevant surfaces are:

* **Checkpoint loading.** Model checkpoints are deserialised with PyTorch. They
  must be loaded with `weights_only=True`; without it a crafted checkpoint
  executes arbitrary code. Treat checkpoints from outside your own training runs
  as untrusted input.
* **Imagery parsing.** GDAL, `rasterio` and `opencv` parse untrusted raster
  data. Keep them patched — see [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md).
* **Command-line arguments.** Modules receive paths from the backend. Do not
  pass them to a shell.

## Deployment security

GAIA is deployed as a whole. The hardening guidance for a running installation —
API key, exposed ports, TLS, GeoServer credentials — lives with the backend:

**[gaia-backend/SECURITY.md](https://github.com/aiprojektgaia/gaia-backend/blob/main/SECURITY.md)**

Read it before putting any part of GAIA on a network.

## Known limitations

* Engine modules run with the same privileges as the backend
  process; there is no sandbox between a module and the host.
* A module that never calls back leaves its step running indefinitely, which
  stalls the whole pipeline — there is no subprocess-level timeout.
* Input limits (tile count, WMS response size and timeouts, raster pixel and
  file counts, comparison complexity) are enforced inside the modules and can be
  tuned with `GAIA_*` environment variables, but they are not a substitute for
  per-process CPU, memory and wall-clock limits set by the deployment.
* Model checkpoints are verified against the SHA-256 configured in
  `segmentation/parameters.json` and refused if it is missing or differs. The
  digest is only as trustworthy as the place you copied it from.

## Audit history

Dependency vulnerabilities and their dispositions, including confirmed false
positives, are recorded in [docs/security-fixes-260817.md](docs/security-fixes-260817.md).
