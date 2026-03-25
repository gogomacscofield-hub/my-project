from __future__ import annotations

from pathlib import Path

import trimesh

from .config import PrinterProfile, SliceSettings
from .gcode import GCodeWriter
from .geometry import center_mesh_on_bed, slice_mesh
from .toolpath import infill_paths, order_paths, perimeter_paths, skirt_paths


def slice_mesh_to_gcode(
    mesh_path: Path,
    output_path: Path,
    slice_settings: SliceSettings,
    printer: PrinterProfile | None = None,
) -> None:
    printer = printer or PrinterProfile()
    mesh = trimesh.load_mesh(mesh_path, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError("Input did not load as a single mesh.")
    if mesh.is_empty:
        raise ValueError("Input mesh is empty.")
    if not mesh.is_watertight:
        raise ValueError("Input mesh must be watertight.")

    working_mesh = center_mesh_on_bed(mesh, (printer.center_x, printer.center_y)) if slice_settings.align_to_bed_center else mesh.copy()
    layers = slice_mesh(working_mesh, slice_settings.layer_height)

    writer = GCodeWriter(printer, line_width=slice_settings.line_width, layer_height=slice_settings.layer_height)
    writer.write_header()

    first_polygons = next((layer.polygons for layer in layers if layer.polygons), [])
    for path in skirt_paths(first_polygons, slice_settings):
        writer.comment("Skirt")
        writer.write_toolpath(path, slice_settings.layer_height, printer.first_layer_speed)

    previous_end = None
    for layer in layers:
        if not layer.polygons:
            continue
        writer.comment(f"LAYER:{layer.index}")
        perimeter = order_paths(perimeter_paths(layer.polygons, slice_settings), previous_end)
        infill_start = perimeter[-1].end_point() if perimeter else previous_end
        infill = order_paths(infill_paths(layer.polygons, slice_settings, layer.index), infill_start)
        speed = printer.first_layer_speed if layer.index == 0 else printer.print_speed
        for path in perimeter + infill:
            writer.write_toolpath(path, layer.z, speed)
            previous_end = path.end_point()

    writer.write_footer()
    writer.save(output_path)
