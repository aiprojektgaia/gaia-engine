from shapely.geometry import (
    Polygon,
    MultiPolygon,
)
import numpy as np
from numpy.polynomial.polynomial import Polynomial

from .utils import _subdivide_polygon, _bezier_curve, _exponential_kernel


def _polygon_smoothing(polygon: Polygon, method: str, subdivide=0, *args, **kwargs):
    if subdivide > 0:
        polygon = _subdivide_polygon(polygon, subdivide)
    smoothing_method = smoothing_methods.get(method)
    if smoothing_method is None:
        raise ValueError(
            f"Smoothing method {method} not found. Supported methods are {list(smoothing_methods.keys())}"
        )
    exterior = smoothing_method(np.array(polygon.exterior.coords[:-1]), *args, **kwargs)

    interiors = [
        smoothing_method(np.array(hole.coords[:-1]), *args, **kwargs)
        for hole in polygon.interiors
    ]

    return Polygon(exterior, interiors)


def _multi_polygon_smoothing(multi_polygon: MultiPolygon, method: str, *args, **kwargs):
    smoothed_polygons = [
        _polygon_smoothing(p, method, *args, **kwargs) for p in multi_polygon.geoms
    ]
    return MultiPolygon(smoothed_polygons)


def _laplacian_smoothing(vertices, alpha=0.5):
    if alpha == 0:
        return vertices
    n = len(vertices)
    smoothed_vertices = np.copy(vertices)

    for i in range(n):

        prev_vertex = vertices[i - 1]

        if i == n - 1:
            next_vertex = vertices[0]
        else:
            next_vertex = vertices[i + 1]

        smoothed_vertices[i] = vertices[i] + alpha * (
            prev_vertex + next_vertex - 2 * vertices[i]
        )

    return smoothed_vertices


def _taubin_smoothing(vertices, alpha=0.5, beta=-0.51, iterations=1):
    smoothed_vertices = np.copy(vertices)

    for _ in range(iterations):
        smoothed_vertices = _laplacian_smoothing(smoothed_vertices, alpha)
        smoothed_vertices = _laplacian_smoothing(smoothed_vertices, beta)

    return smoothed_vertices


def _bezier_smoothing(vertices, smoothness=0.5, num_points=10):
    """
    Smooths a polygon using Bezier curves, ensuring smoothness at all vertices.

    Args:
        polygon (Polygon): The input polygon to smooth.
        smoothness (float): Controls the 'tightness' of the smoothing.

    Returns:
        Polygon: A new, smoothed polygon.
    """

    num_vertices = len(vertices)
    smoothed_coords = []

    for i in range(num_vertices):
        p0 = np.array(vertices[i - 1])
        p1 = np.array(vertices[i])
        p2 = np.array(vertices[(i + 1) % num_vertices])
        p3 = np.array(vertices[(i + 2) % num_vertices])

        # Calculate control points
        ctrl1 = p1 + smoothness * (p2 - p0) / 3
        ctrl2 = p2 - smoothness * (p3 - p1) / 3

        # Generate Bezier curve for this segment
        if i == 0:
            # For the first point, add the entire curve
            bezier_points = _bezier_curve(p1, ctrl1, ctrl2, p2, num_points=num_points)
        else:
            # For subsequent points, add the curve excluding the first point to avoid duplication
            bezier_points = _bezier_curve(p1, ctrl1, ctrl2, p2, num_points=num_points)[
                1:
            ]

        smoothed_coords.extend(bezier_points)

    # Create a new polygon from the smoothed coordinates
    return Polygon(smoothed_coords)


def _chaikin_smoothing(vertices, iterations=1, weight=0.75):
    """
    Smooths a polygon using the Chaikin algorithm.

    :param vertices: List of points defining the polygon.
    :param iterations: Number of smoothing iterations to apply.
    :return: List of smoothed points.
    """

    # vertices = np.vstack((vertices, vertices[0]))
    alpha = weight
    beta = 1 - alpha

    def chaikin_cut(vertices):
        vertices = np.vstack((vertices, vertices[0]))

        # Preallocate the array for new points
        new_verts = np.empty((2 * (len(vertices) - 1), 2))

        # Calculate the q and r points for each segment
        new_verts[0::2] = alpha * vertices[:-1] + beta * vertices[1:]
        new_verts[1::2] = beta * vertices[:-1] + alpha * vertices[1:]

        # Append the last point manually (avoid slicing errors)
        # new_verts[-1] = vertices[-1]

        return new_verts

    iterations = int(iterations)
    for _ in range(iterations):
        vertices = chaikin_cut(vertices)

    return vertices


def _paek_smoothing(polygon, smoothing_factor=1.0):
    """
    Smooth a polygon using the PAEK algorithm.

    Parameters:
    polygon (numpy.ndarray): The input polygon, a 2D numpy array of shape (n, 2),
                             where n is the number of vertices.
    smoothing_factor (float): The smoothing factor determines how much to smooth.
                              Higher values result in more smoothing.

    Returns:
    numpy.ndarray: The smoothed polygon, a 2D numpy array of shape (n, 2).
    """

    def weight_function(t, smoothing_factor):
        return np.exp(-(t**2) / smoothing_factor)

    n = polygon.shape[0]
    smoothed_polygon = np.zeros_like(polygon)

    for i in range(n):
        weighted_sum = np.zeros(2)
        total_weight = 0.0
        for j in range(n):
            distance = np.linalg.norm(polygon[i] - polygon[j])
            weight = weight_function(distance, smoothing_factor)
            weighted_sum += weight * polygon[j]
            total_weight += weight

        smoothed_polygon[i] = weighted_sum / total_weight

    return smoothed_polygon


def _kernel_smoothing(vertices, kernel_fn, alpha=0.5):
    """
    Smooths a polygon using a kernel filter.

    Args:
        vertices (np.ndarray): The input vertices of the polygon.
        kernel_size (int): The size of the kernel.

    Returns:
        np.ndarray: The smoothed vertices.
    """

    n = len(vertices)
    smoothed_vertices = np.copy(vertices)

    for i in range(n):

        prev_vertex = vertices[i - 1]
        next_vertex = vertices[(i + 1) % n]

        smoothed_vertices[i] = np.mean(
            np.array([prev_vertex, vertices[i], next_vertex]), axis=0
        )

    return smoothed_vertices


smoothing_methods = {
    "laplacian": _laplacian_smoothing,
    "taubin": _taubin_smoothing,
    "bezier": _bezier_smoothing,
    "chaikin": _chaikin_smoothing,
    "paek": _paek_smoothing,
}
