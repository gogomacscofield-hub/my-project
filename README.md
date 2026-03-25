# fdm-slicer

`fdm-slicer` is a small experimental project for slicing watertight meshes into FDM G-code with cleaner seams, smoother contours, and optional arc output.

## What this project does

- Loads a watertight mesh such as STL
- Slices the model into horizontal layers
- Generates perimeter and infill toolpaths
- Emits FDM-style G-code
- Reorders paths to reduce visible seam wandering
- Converts circular runs into `G2` arc moves when possible

## Highlights

- GitHub-friendly `src/` layout and installable CLI
- Centers the model on the print bed by default
- Uses a fixed seam strategy so closed loops do not wander layer to layer
- Prints inner walls before the outside wall for better visible surfaces
- Fits circular runs into `G2` and `G3` arcs when possible
- Supports `lines`, `grid`, `zigzag`, and `concentric` infill

## Status

This is an experimental slicer, not a full replacement for Cura, OrcaSlicer, or PrusaSlicer. It is best used as a small research or hobby project for generating cleaner custom G-code from simple watertight meshes.

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

## Installation

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

## Where files go

Input mesh:
- Put your `.stl` anywhere you want
- Example: `models/input.stl`
- Example absolute path: `/Users/you/project/models/input.stl`

Output G-code:
- You choose the output location in the command
- Example: `output/gcode/part.gcode`
- The tool will create the parent folder if needed

Typical structure:

```text
models/
  input.stl
output/
  gcode/
    part.gcode
```

## Quick start

```bash
fdm-slicer models/input.stl output/gcode/part.gcode
```

If you have not installed the CLI entrypoint yet, you can run it like this:

```bash
PYTHONPATH=src python3 -m fdm_slicer.cli models/input.stl output/gcode/part.gcode
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

The generated file will be written to:

```text
/Users/chenghongkai/Documents/Playground/output/gcode/wan-guan-refined.gcode
```

## Main command format

```bash
fdm-slicer INPUT_STL OUTPUT_GCODE [options]
```

Example:

```bash
fdm-slicer ./models/input.stl ./output/gcode/output.gcode --wall-count 3 --infill-pattern concentric
```

## Parameters

### Geometry and slicing

- `--layer-height`
  - Layer thickness in mm
  - Lower values give finer detail and slower prints
  - Example: `0.12`, `0.2`, `0.28`

- `--line-width`
  - Extrusion line width in mm
  - Usually close to nozzle size or slightly larger
  - Example: `0.42`, `0.45`, `0.48`

- `--wall-count`
  - Number of perimeter shells
  - Higher values give stronger parts and smoother outer walls

### Infill

- `--infill-density`
  - Infill ratio from `0.0` to `1.0`
  - Example: `0.12` means 12 percent style spacing

- `--infill-pattern`
  - Choices: `lines`, `grid`, `zigzag`, `concentric`
  - `concentric` is often visually cleaner for round tube-like parts

### Path smoothing

- `--contour-tolerance`
  - Controls how aggressively the contour is simplified
  - Higher value means smoother but less exact geometry
  - Start around `0.03` to `0.08`

- `--minimum-segment-length`
  - Removes tiny short moves that make the G-code noisy
  - Increase this if the preview still looks too chattery

- `--arc-tolerance`
  - Controls arc fitting error tolerance
  - Smaller values preserve shape more tightly
  - Larger values produce more `G2` and `G3` moves

- `--minimum-arc-points`
  - Minimum number of points before the slicer tries to fit an arc

- `--minimum-arc-angle-deg`
  - Minimum angular sweep before an arc is emitted

### Seam control

- `--seam-strategy`
  - Choices: `xmin`, `xmax`, `ymin`, `ymax`
  - This picks where closed loops tend to start and end
  - Use it to hide the seam on a less visible side of the part

### Bed and placement

- `--bed-width`
- `--bed-depth`
- `--center-x`
- `--center-y`
  - Used when automatically centering the model on the print bed

- `--no-center`
  - Disables automatic centering
  - Use this if your mesh is already placed exactly where you want

### Printer and extrusion

- `--nozzle-temperature`
- `--bed-temperature`
- `--fan-speed`
- `--travel-speed`
- `--print-speed`
- `--first-layer-speed`
- `--filament-diameter`
- `--extrusion-multiplier`
  - These control the generated G-code motion and extrusion assumptions

## How to tune parameters

If the preview still looks rough:

- Lower `--contour-tolerance`
- Lower `--arc-tolerance`
- Lower `--minimum-segment-length`

If the G-code is too dense and noisy:

- Raise `--contour-tolerance`
- Raise `--minimum-segment-length`
- Raise `--arc-tolerance` a little

If you want smoother round walls:

- Use `--infill-pattern concentric`
- Keep `--wall-count 3` or more
- Try `--seam-strategy xmin` or `ymin`

If you want stronger parts:

- Increase `--wall-count`
- Increase `--infill-density`

## Recommended starting presets

General prototype:

```bash
fdm-slicer models/input.stl output/gcode/part.gcode \
  --layer-height 0.2 \
  --wall-count 3 \
  --infill-density 0.12 \
  --infill-pattern concentric
```

Higher detail:

```bash
fdm-slicer models/input.stl output/gcode/part.gcode \
  --layer-height 0.12 \
  --contour-tolerance 0.03 \
  --arc-tolerance 0.02 \
  --minimum-segment-length 0.05
```

Faster rougher draft:

```bash
fdm-slicer models/input.stl output/gcode/part.gcode \
  --layer-height 0.28 \
  --contour-tolerance 0.08 \
  --minimum-segment-length 0.12
```

## Development

Run tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

Run without installing the CLI:

```bash
PYTHONPATH=src python3 -m fdm_slicer.cli models/input.stl output/gcode/part.gcode
```

## Current limitations

- This is still an experimental slicer, not a replacement for Cura, OrcaSlicer, or PrusaSlicer.
- The generated start and end G-code are generic and should be tuned for your printer.
- Arc support depends on your printer firmware and preview tool.
- Supports only simple watertight mesh input well
- Does not yet handle supports, bridges, top and bottom skin planning, or advanced travel optimization
