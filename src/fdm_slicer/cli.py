from __future__ import annotations

import argparse
from pathlib import Path

from .config import PrinterProfile, SliceSettings
from .pipeline import slice_mesh_to_gcode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimental FDM slicer with smoother G-code output.")
    parser.add_argument("input_mesh", type=Path)
    parser.add_argument("output_gcode", type=Path)
    parser.add_argument("--layer-height", type=float, default=0.2)
    parser.add_argument("--line-width", type=float, default=0.45)
    parser.add_argument("--wall-count", type=int, default=3)
    parser.add_argument("--infill-density", type=float, default=0.12)
    parser.add_argument("--infill-pattern", choices=["lines", "grid", "zigzag", "concentric"], default="concentric")
    parser.add_argument("--skirt-loops", type=int, default=1)
    parser.add_argument("--skirt-distance", type=float, default=4.0)
    parser.add_argument("--contour-tolerance", type=float, default=0.05)
    parser.add_argument("--minimum-segment-length", type=float, default=0.08)
    parser.add_argument("--arc-tolerance", type=float, default=0.035)
    parser.add_argument("--minimum-arc-points", type=int, default=5)
    parser.add_argument("--minimum-arc-angle-deg", type=float, default=12.0)
    parser.add_argument("--seam-strategy", choices=["xmin", "xmax", "ymin", "ymax"], default="xmin")
    parser.add_argument("--bed-width", type=float, default=220.0)
    parser.add_argument("--bed-depth", type=float, default=220.0)
    parser.add_argument("--center-x", type=float, default=110.0)
    parser.add_argument("--center-y", type=float, default=110.0)
    parser.add_argument("--nozzle-temperature", type=int, default=205)
    parser.add_argument("--bed-temperature", type=int, default=60)
    parser.add_argument("--fan-speed", type=int, default=255)
    parser.add_argument("--travel-speed", type=float, default=7200.0)
    parser.add_argument("--print-speed", type=float, default=2100.0)
    parser.add_argument("--first-layer-speed", type=float, default=1200.0)
    parser.add_argument("--filament-diameter", type=float, default=1.75)
    parser.add_argument("--extrusion-multiplier", type=float, default=1.0)
    parser.add_argument("--no-center", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    slice_settings = SliceSettings(
        layer_height=args.layer_height,
        line_width=args.line_width,
        wall_count=args.wall_count,
        infill_density=args.infill_density,
        infill_pattern=args.infill_pattern,
        skirt_loops=args.skirt_loops,
        skirt_distance=args.skirt_distance,
        contour_tolerance=args.contour_tolerance,
        minimum_segment_length=args.minimum_segment_length,
        arc_tolerance=args.arc_tolerance,
        minimum_arc_points=args.minimum_arc_points,
        minimum_arc_angle_deg=args.minimum_arc_angle_deg,
        seam_strategy=args.seam_strategy,
        align_to_bed_center=not args.no_center,
    )
    printer = PrinterProfile(
        bed_width=args.bed_width,
        bed_depth=args.bed_depth,
        center_x=args.center_x,
        center_y=args.center_y,
        nozzle_temperature=args.nozzle_temperature,
        bed_temperature=args.bed_temperature,
        fan_speed=args.fan_speed,
        travel_speed=args.travel_speed,
        print_speed=args.print_speed,
        first_layer_speed=args.first_layer_speed,
        filament_diameter=args.filament_diameter,
        extrusion_multiplier=args.extrusion_multiplier,
    )
    slice_mesh_to_gcode(args.input_mesh, args.output_gcode, slice_settings, printer)
    print(f"Wrote {args.output_gcode}")


if __name__ == "__main__":
    main()
