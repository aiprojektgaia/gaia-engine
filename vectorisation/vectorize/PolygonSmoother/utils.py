import numpy as np
from shapely.geometry import Polygon, LineString
from math import ceil


def _subdivide_polygon(polygon: Polygon, spacing):
    new_coords = []
    coords = list(polygon.exterior.coords)
    for i in range(len(coords) - 1):

        segment = LineString((coords[i], coords[i + 1]))
        length = segment.length
        num_points = round(length / spacing)
        if num_points > 0:
            step_size = length / num_points
            for i in range(num_points):
                new_coords.append(segment.interpolate(i * step_size).coords[0])
        else:
            new_coords.append(segment.interpolate(0).coords[0])
    polygon = Polygon(new_coords)
    return polygon


def _bezier_curve(p0, p1, p2, p3, num_points=100):
    """
    Calculate a Bezier curve from four points.

    Args:
        p0, p1, p2, p3: The start point, two control points, and end point of the curve.
        num_points (int): Number of points to generate on the curve.

    Returns:
        np.ndarray: Array of points on the Bezier curve.
    """

    t = np.linspace(0, 1, num_points).reshape(-1, 1)
    curve = (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t**2 * p2
        + t**3 * p3
    )
    return curve


def _exponential_kernel(x, y, sigma=1.0):
    return np.exp(-np.linalg.norm(x - y) ** 2 / (2 * sigma**2))
