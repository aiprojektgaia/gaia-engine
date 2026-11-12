# gaia-engine documentation

| Document | Contents |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Module boundaries, data flow, tiling, per-module internals |
| [MODELS.md](MODELS.md) | Checkpoints, configuration, adding a model or object class |
| [DEPENDENCIES.md](DEPENDENCIES.md) | Per-module environments, the GDAL rule, licences |
| [security-fixes-260817.md](security-fixes-260817.md) | Vulnerability audit record and post-mortem |
| [architecture/](architecture/) | Diagrams |

Module-level documentation lives with the code:
[core/wms_tiler](../core/wms_tiler/README.md),
[core/image_bitter](../core/image_bitter/README.md),
[segmentation](../segmentation/README.md),
[vectorisation](../vectorisation/README.md),
[comparison](../comparison/README.md).

The system-level view — how the backend, engine and QGIS client fit together —
is in [gaia-backend/docs/ARCHITECTURE.md](https://github.com/aiprojektgaia/gaia-backend/blob/main/docs/ARCHITECTURE.md).
