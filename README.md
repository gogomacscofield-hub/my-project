# fdm-slicer

`fdm-slicer` is a small experimental project for slicing watertight meshes into FDM G-code with cleaner seams, smoother contours, and optional arc output.

## Highlights

- GitHub-friendly `src/` layout and installable CLI
- Centers the model on the print bed by default
- Uses a fixed seam strategy so closed loops do not wander layer to layer
- Prints inner walls before the outside wall for better visible surfaces
- Fits circular runs into `G2` and `G3` arcs when possible
- Supports `lines`, `grid`, `zigzag`, and `concentric` infill

## Layout

```text
src/fdm_slicer/
  cli.py
  config.py
  geometry.py
  gcode.py
  pipeline.py
  toolpath.py
tests/
pyproject.toml
requirements.txt
README.md
```

## Install

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

## Quick start

```bash
fdm-slicer input.stl output.gcode
```

## Example for your STL

```bash
PYTHONPATH=src python3 -m fdm_slicer.cli \
  "/Users/chenghongkai/Documents/Playground/弯管.STL" \
  "/Users/chenghongkai/Documents/Playground/output/gcode/wan-guan-refined.gcode" \
  --wall-count 3 \
  --infill-pattern concentric \
  --infill-density 0.12 \
  --contour-tolerance 0.05 \
  --arc-tolerance 0.035 \
  --seam-strategy xmin
```

## Notes

- This is still an experimental slicer, not a replacement for Cura, OrcaSlicer, or PrusaSlicer.
- The generated start and end G-code are generic and should be tuned for your printer.
- Arc support depends on your printer firmware and preview tool.
