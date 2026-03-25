from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np
import trimesh
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.ops import unary_union


Coordinate = Tuple[float, float]


@dataclass
class Layer:
    index: int
    z: float
    polygons: List[Polygon]


def flatten_polygons(geometry) -> List[Polygon]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return [polygon for polygon in geometry.geoms if not polygon.is_empty]
    if isinstance(geometry, GeometryCollection):
        parts: List[Polygon] = []
        for item in geometry.geoms:
            parts.extend(flatten_polygons(item))
        return parts
    return []


def orient_and_repair(polygons: Sequence[Polygon]) -> List[Polygon]:
    repaired = [polygon.buffer(0) for polygon in polygons if polygon.area > 1e-6]
    if not repaired:
        return []
    return flatten_polygons(unary_union(repaired))


def center_mesh_on_bed(mesh: trimesh.Trimesh, bed_center: Coordinate) -> trimesh.Trimesh:
    shifted = mesh.copy()
    bounds = shifted.bounds
    model_center_x = float(bounds[0][0] + bounds[1][0]) / 2.0
    model_center_y = float(bounds[0][1] + bounds[1][1]) / 2.0
    move_x = bed_center[0] - model_center_x
    move_y = bed_center[1] - model_center_y
    move_z = -float(bounds[0][2])
    shifted.apply_translation((move_x, move_y, move_z))
    return shifted


def planar_ring_to_world(points, to_3d) -> List[Coordinate]:
    data = np.asarray(points, dtype=float)
    if len(data) == 0:
        return []
    if data.shape[1] == 2:
        data = np.column_stack([data, np.zeros(len(data))])
    transformed = trimesh.transform_points(data, to_3d)
    return [(float(x), float(y)) for x, y in transformed[:, :2]]


def planar_polygon_to_world(polygon: Polygon, to_3d) -> Polygon:
    exterior = planar_ring_to_world(polygon.exterior.coords, to_3d)
    interiors = [planar_ring_to_world(interior.coords, to_3d) for interior in polygon.interiors]
    return Polygon(exterior, interiors)


def slice_mesh(mesh: trimesh.Trimesh, layer_height: float) -> List[Layer]:
    z_max = float(mesh.bounds[1][2])
    z = layer_height / 2.0
    index = 0
    layers: List[Layer] = []
    while z <= z_max + 1e-9:
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is None:
            layers.append(Layer(index=index, z=z, polygons=[]))
            z += layer_height
            index += 1
            continue
        planar, to_3d = section.to_2D()
        polygons = [planar_polygon_to_world(polygon, to_3d) for polygon in planar.polygons_full]
        layers.append(Layer(index=index, z=z, polygons=orient_and_repair(polygons)))
        z += layer_height
        index += 1
    return layers
