from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from shapely import affinity
from shapely.geometry import GeometryCollection, LineString, MultiLineString, Point, Polygon
from shapely.ops import unary_union

from .config import SliceSettings
from .geometry import Coordinate, flatten_polygons


@dataclass
class Segment:
    kind: str
    end: Coordinate
    center_offset: Coordinate | None = None
    clockwise: bool = False


@dataclass
class Toolpath:
    start: Coordinate
    segments: List[Segment]
    closed: bool

    def end_point(self) -> Coordinate:
        if not self.segments:
            return self.start
        return self.segments[-1].end

    def vertices(self) -> List[Coordinate]:
        points = [self.start]
        points.extend(segment.end for segment in self.segments)
        return points


def remove_short_segments(points: Sequence[Coordinate], minimum_length: float) -> List[Coordinate]:
    cleaned: List[Coordinate] = []
    for point in points:
        if not cleaned or math.dist(cleaned[-1], point) >= minimum_length:
            cleaned.append(point)
    return cleaned


def simplify_ring(points: Sequence[Coordinate], settings: SliceSettings) -> List[Coordinate]:
    if len(points) < 4:
        return list(points)
    line = LineString(points)
    simplified = line.simplify(settings.contour_tolerance, preserve_topology=False)
    coords = remove_short_segments(list(simplified.coords), settings.minimum_segment_length)
    if len(coords) < 3:
        coords = remove_short_segments(list(points), settings.minimum_segment_length)
    if len(coords) >= 2 and math.dist(coords[0], coords[-1]) < settings.minimum_segment_length:
        coords = coords[:-1]
    return coords


def seam_score(point: Coordinate, strategy: str) -> Tuple[float, float]:
    x, y = point
    if strategy == "xmin":
        return (x, y)
    if strategy == "xmax":
        return (-x, y)
    if strategy == "ymin":
        return (y, x)
    if strategy == "ymax":
        return (-y, x)
    return (x, y)


def rotate_to_seam(points: Sequence[Coordinate], strategy: str) -> List[Coordinate]:
    if not points:
        return []
    best_index = min(range(len(points)), key=lambda idx: seam_score(points[idx], strategy))
    pts = list(points)
    return pts[best_index:] + pts[:best_index]


def polygon_shells(polygon: Polygon, settings: SliceSettings) -> List[Polygon]:
    shells: List[Polygon] = []
    current = polygon
    for _ in range(settings.wall_count):
        if current.is_empty or current.area <= 1e-6:
            break
        shells.extend(flatten_polygons(current))
        current = current.buffer(-settings.line_width, join_style=2)
    return shells


def ring_orientation(points: Sequence[Coordinate]) -> float:
    area = 0.0
    for current, nxt in zip(points, points[1:] + points[:1]):
        area += current[0] * nxt[1] - nxt[0] * current[1]
    return area / 2.0


def fit_circle(points: Sequence[Coordinate]) -> Tuple[Coordinate, float, float]:
    data = np.asarray(points, dtype=float)
    x = data[:, 0]
    y = data[:, 1]
    a = np.column_stack((2.0 * x, 2.0 * y, np.ones(len(data))))
    b = x * x + y * y
    cx, cy, c = np.linalg.lstsq(a, b, rcond=None)[0]
    radius = math.sqrt(max(c + cx * cx + cy * cy, 0.0))
    distances = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    error = float(np.max(np.abs(distances - radius)))
    return (float(cx), float(cy)), float(radius), error


def signed_turns(points: Sequence[Coordinate]) -> bool:
    signs = []
    for a, b, c in zip(points, points[1:], points[2:]):
        ab = (b[0] - a[0], b[1] - a[1])
        bc = (c[0] - b[0], c[1] - b[1])
        cross = ab[0] * bc[1] - ab[1] * bc[0]
        if abs(cross) > 1e-9:
            signs.append(math.copysign(1.0, cross))
    return not signs or all(sign == signs[0] for sign in signs)


def arc_angle(center: Coordinate, start: Coordinate, end: Coordinate, clockwise: bool) -> float:
    start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
    end_angle = math.atan2(end[1] - center[1], end[0] - center[0])
    if clockwise:
        delta = (start_angle - end_angle) % (2.0 * math.pi)
    else:
        delta = (end_angle - start_angle) % (2.0 * math.pi)
    return delta


def try_arc(points: Sequence[Coordinate], settings: SliceSettings) -> Segment | None:
    if len(points) < settings.minimum_arc_points or not signed_turns(points):
        return None
    center, radius, error = fit_circle(points)
    if error > settings.arc_tolerance or radius < settings.line_width:
        return None
    clockwise = ring_orientation(points) < 0.0
    angle = arc_angle(center, points[0], points[-1], clockwise)
    if math.degrees(angle) < settings.minimum_arc_angle_deg:
        return None
    start = points[0]
    end = points[-1]
    offset = (center[0] - start[0], center[1] - start[1])
    return Segment(kind="arc", end=end, center_offset=offset, clockwise=clockwise)


def segmentize(points: Sequence[Coordinate], closed: bool, settings: SliceSettings) -> Toolpath:
    if len(points) < 2:
        return Toolpath(start=points[0], segments=[], closed=closed)
    work = list(points)
    if closed:
        work = work + [work[0]]
    segments: List[Segment] = []
    cursor = 0
    while cursor < len(work) - 1:
        best_arc: Segment | None = None
        best_end = None
        max_end = min(len(work), cursor + 12)
        for end_idx in range(cursor + settings.minimum_arc_points, max_end + 1):
            candidate = try_arc(work[cursor:end_idx], settings)
            if candidate is not None:
                best_arc = candidate
                best_end = end_idx - 1
        if best_arc is not None and best_end is not None:
            segments.append(best_arc)
            cursor = best_end
            continue
        segments.append(Segment(kind="line", end=work[cursor + 1]))
        cursor += 1
    return Toolpath(start=work[0], segments=segments, closed=closed)


def path_distance(toolpath: Toolpath, point: Coordinate | None) -> float:
    if point is None:
        return 0.0
    return math.dist(toolpath.start, point)


def order_paths(paths: Sequence[Toolpath], current_point: Coordinate | None) -> List[Toolpath]:
    pending = list(paths)
    ordered: List[Toolpath] = []
    cursor = current_point
    while pending:
        index = min(range(len(pending)), key=lambda idx: path_distance(pending[idx], cursor))
        selected = pending.pop(index)
        ordered.append(selected)
        cursor = selected.end_point()
    return ordered


def perimeter_paths(polygons: Sequence[Polygon], settings: SliceSettings) -> List[Toolpath]:
    paths: List[Toolpath] = []
    for polygon in polygons:
        shells = polygon_shells(polygon, settings)
        shell_paths: List[Toolpath] = []
        for shell in shells:
            outer = rotate_to_seam(simplify_ring(list(shell.exterior.coords), settings), settings.seam_strategy)
            if len(outer) >= 3:
                shell_paths.append(segmentize(outer, closed=True, settings=settings))
            for interior in shell.interiors:
                hole = rotate_to_seam(simplify_ring(list(interior.coords), settings), settings.seam_strategy)
                if len(hole) >= 3:
                    shell_paths.append(segmentize(hole, closed=True, settings=settings))
        paths.extend(reversed(shell_paths))
    return paths


def infill_region(polygons: Sequence[Polygon], settings: SliceSettings):
    inset = settings.wall_count * settings.line_width
    regions = []
    for polygon in polygons:
        regions.extend(flatten_polygons(polygon.buffer(-inset, join_style=2)))
    if not regions:
        return GeometryCollection()
    return unary_union(regions)


def line_fill(region, spacing: float, angle_deg: float, settings: SliceSettings, zigzag: bool) -> List[Toolpath]:
    if region.is_empty:
        return []
    minx, miny, maxx, maxy = region.bounds
    diagonal = math.hypot(maxx - minx, maxy - miny) + spacing * 4.0
    center = ((minx + maxx) / 2.0, (miny + maxy) / 2.0)
    rotated = affinity.rotate(region, -angle_deg, origin=center)
    rminx, rminy, rmaxx, rmaxy = rotated.bounds
    y = rminy - spacing
    reverse = False
    paths: List[Toolpath] = []
    while y <= rmaxy + spacing:
        baseline = LineString([(rminx - diagonal, y), (rmaxx + diagonal, y)])
        clipped = rotated.intersection(baseline)
        if isinstance(clipped, LineString):
            pieces: Iterable[LineString] = [clipped]
        elif isinstance(clipped, MultiLineString):
            pieces = sorted(clipped.geoms, key=lambda line: line.bounds[0])
        else:
            pieces = []
        for piece in pieces:
            coords = [affinity.rotate(Point(x, yy), angle_deg, origin=center).coords[0] for x, yy in piece.coords]
            coords = remove_short_segments(coords, settings.minimum_segment_length)
            if len(coords) < 2:
                continue
            if zigzag and reverse:
                coords.reverse()
            paths.append(segmentize(coords, closed=False, settings=settings))
            if zigzag:
                reverse = not reverse
        y += spacing
    return paths


def concentric_fill(region, settings: SliceSettings) -> List[Toolpath]:
    current = region
    paths: List[Toolpath] = []
    spacing = max(settings.line_width, settings.line_width / max(settings.infill_density, 0.05))
    while not current.is_empty:
        polygons = flatten_polygons(current)
        if not polygons:
            break
        for polygon in polygons:
            outer = rotate_to_seam(simplify_ring(list(polygon.exterior.coords), settings), settings.seam_strategy)
            if len(outer) >= 3:
                paths.append(segmentize(outer, closed=True, settings=settings))
            for interior in polygon.interiors:
                hole = rotate_to_seam(simplify_ring(list(interior.coords), settings), settings.seam_strategy)
                if len(hole) >= 3:
                    paths.append(segmentize(hole, closed=True, settings=settings))
        current = unary_union([polygon.buffer(-spacing, join_style=2) for polygon in polygons])
    return paths


def infill_paths(polygons: Sequence[Polygon], settings: SliceSettings, layer_index: int) -> List[Toolpath]:
    region = infill_region(polygons, settings)
    if region.is_empty or settings.infill_density <= 0.0:
        return []
    spacing = max(settings.line_width, settings.line_width / max(settings.infill_density, 0.05))
    if settings.infill_pattern == "concentric":
        return concentric_fill(region, settings)
    angle = 45.0 if layer_index % 2 == 0 else -45.0
    if settings.infill_pattern == "grid":
        return line_fill(region, spacing, 45.0, settings, zigzag=False) + line_fill(region, spacing, -45.0, settings, zigzag=False)
    if settings.infill_pattern == "zigzag":
        return line_fill(region, spacing, angle, settings, zigzag=True)
    return line_fill(region, spacing, angle, settings, zigzag=False)


def skirt_paths(polygons: Sequence[Polygon], settings: SliceSettings) -> List[Toolpath]:
    if settings.skirt_loops <= 0 or not polygons:
        return []
    unioned = unary_union(polygons)
    loops: List[Toolpath] = []
    for loop_index in range(settings.skirt_loops):
        shell = unioned.buffer(settings.skirt_distance + loop_index * settings.line_width, join_style=2)
        for polygon in flatten_polygons(shell):
            outer = rotate_to_seam(simplify_ring(list(polygon.exterior.coords), settings), settings.seam_strategy)
            if len(outer) >= 3:
                loops.append(segmentize(outer, closed=True, settings=settings))
    return loops
