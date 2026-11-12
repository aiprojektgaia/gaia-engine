# Architectural diagrams

Diagrams for the engine and the wider GAIA system.

Current written architecture:

- [Engine architecture](../ARCHITECTURE.md) — module boundaries, data flow,
  tiling, per-module internals.
- [System architecture](https://github.com/aiprojektgaia/gaia-backend/blob/main/docs/ARCHITECTURE.md) — how the
  backend, engine and QGIS client fit together. Contains a Mermaid component
  diagram and the pipeline table.

Both documents embed their diagrams as Mermaid, which GitHub renders inline, so
they stay versioned with the text rather than drifting as stale images.

Add exported diagrams (`.png`, `.svg`, `.drawio`) to this folder when a picture
genuinely beats the source — data-flow sketches, deployment topologies — and
link them from the document they support. Keep the editable source alongside any
export.
