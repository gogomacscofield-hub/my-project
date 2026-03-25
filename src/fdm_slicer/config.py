from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PrinterProfile:
    bed_width: float = 220.0
    bed_depth: float = 220.0
    center_x: float = 110.0
    center_y: float = 110.0
    nozzle_temperature: int = 205
    bed_temperature: int = 60
    fan_speed: int = 255
    travel_speed: float = 7200.0
    print_speed: float = 2100.0
    first_layer_speed: float = 1200.0
    filament_diameter: float = 1.75
    extrusion_multiplier: float = 1.0


@dataclass
class SliceSettings:
    layer_height: float = 0.2
    line_width: float = 0.45
    wall_count: int = 3
    infill_density: float = 0.12
    infill_pattern: str = "concentric"
    skirt_loops: int = 1
    skirt_distance: float = 4.0
    contour_tolerance: float = 0.05
    minimum_segment_length: float = 0.08
    arc_tolerance: float = 0.035
    minimum_arc_points: int = 5
    minimum_arc_angle_deg: float = 12.0
    seam_strategy: str = "xmin"
    align_to_bed_center: bool = True
