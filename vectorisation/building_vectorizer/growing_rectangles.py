import cv2
from shapely.geometry import box, Polygon
import numpy as np
from scipy.ndimage import binary_fill_holes, rotate
from shapely.ops import unary_union
from shapely.affinity import rotate as shapely_rotate
from shapely.affinity import translate as shapely_translate
from shapely.affinity import scale as shapely_scale

import largestinteriorrectangle as lir


def load_mask(image_path):
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    image = image.astype(np.uint8)
    return image


def fill_holes(mask):
    filled_mask = np.zeros_like(mask)
    binary_fill_holes(mask, output=filled_mask)

    return filled_mask


def get_obb(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0:
        return None
    largest_contour = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(largest_contour)
    return rect


def rotate_mask(mask, rotation_angle):
    o_center = (mask.shape[1] // 2, mask.shape[0] // 2)
    rotate_mask = rotate(mask, rotation_angle, reshape=True, order=1)
    center = (rotate_mask.shape[1] // 2, rotate_mask.shape[0] // 2)
    offset = (center[0] - o_center[0], center[1] - o_center[1])
    return rotate_mask, center, offset


def axis_align_mask(mask):
    rect = get_obb(mask)
    if rect is None:
        return mask, 0
    angle = rect[2]
    angle = angle if angle < -45 else angle + 90
    rotated_mask, cp, offset = rotate_mask(mask, angle)
    return rotated_mask, angle, cp, offset


def get_next_contour(mask, min_area=0):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0:
        return None
    largest_contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest_contour) <= min_area:
        return None
    return largest_contour


def get_lir(mask, min_area=0):
    next_contour = get_next_contour(mask, min_area)
    if next_contour is None:
        return None
    mask_lir = lir.lir(mask.astype(bool), contour=next_contour[:, 0, :])
    lir_area = mask_lir[2] * mask_lir[3]

    return mask_lir


def lir_to_rect(mask_lir):
    pt1 = (mask_lir[0], mask_lir[1])
    pt2 = (pt1[0] + mask_lir[2] - 1, pt1[1] + mask_lir[3] - 1)
    rect = (pt1, pt2)
    return rect


def close_gaps(mask, kernel_size=5):
    # Create a kernel
    kernel_size = int(round(kernel_size))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = np.ones((kernel_size, kernel_size), np.uint8)

    # Perform the close operation
    closed_mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    return closed_mask


def crop_out_rect(mask, rect):
    cv2.rectangle(mask, rect[0], rect[1], 0, -1)
    return mask


def calculate_poly_side_length(poly):
    verts = np.array(poly.exterior.coords)
    sides = verts[:-1] - verts[1:]
    side_lengths = np.linalg.norm(sides, axis=1)
    return side_lengths, verts


def grow_footprint(
    building_mask, min_area=100, shortest_side=15, apply_smoothing=False
) -> Polygon:
    mask, angle, cp, offset = axis_align_mask(building_mask)
    rects = []
    itr = 0
    while True:
        itr += 1
        mask_lir = get_lir(mask, min_area)
        if mask_lir is not None:
            lir_area = mask_lir[2] * mask_lir[3]
            lir_shortest_side = min(mask_lir[2], mask_lir[3])
            mask_lir_rect = lir_to_rect(mask_lir)
            # plot_mask_and_rect(mask, mask_lir_rect)
            mask = crop_out_rect(mask, mask_lir_rect)
            if lir_area > min_area and lir_shortest_side > (shortest_side / 1):
                rects.append(
                    box(
                        mask_lir_rect[0][0] - 1,
                        mask_lir_rect[0][1] - 1,
                        mask_lir_rect[1][0] + 1,
                        mask_lir_rect[1][1] + 1,
                    )
                )
        else:
            # print(f"completed {itr} iterations")
            break
    ur = unary_union(rects)
    # ur = ur.simplify(shortest_side/5)
    if ur.is_empty:
        return Polygon()
    if ur.geom_type == "GeometryCollection":
        print(ur)
        footprints = list(ur.geoms)
        print(footprints)
        ur = max(footprints, key=lambda x: x.area)
    if ur.geom_type == "MultiPolygon":
        footprints = list(ur.geoms)
        ur = max(footprints, key=lambda x: x.area)

    rotated_ur = shapely_rotate(ur, angle, origin=(cp[0], cp[1]))
    rotated_ur = shapely_translate(rotated_ur, xoff=-offset[0], yoff=-offset[1])
    # flip the y-axis
    # rotated_ur = shapely_scale(rotated_ur, xfact=1, yfact=-1, origin=(0,0))
    if apply_smoothing:
        rotated_ur = smooth_walls(rotated_ur, shortest_wall=shortest_side)
    return rotated_ur


def smooth_walls(footprint, shortest_wall=15) -> Polygon:
    pl, verts = calculate_poly_side_length(footprint)
    if len(verts) <= 5:
        return footprint

    # walls within 20% of the shortest wall length are
    # candidates for culling
    culling_candidate = shortest_wall * 1.2

    remove = set()
    pl = list(pl)
    pl.append(pl[0])
    for i in range(len(pl) - 1):
        if pl[i - 1] < culling_candidate and pl[i + 1] < culling_candidate:
            remove.add(i)
            remove.add(i + 1)
    remove = sorted(list(remove))
    new_verts = [v for i, v in enumerate(verts) if i not in remove]
    if len(new_verts) < 5:
        return footprint
    new_fp = Polygon(new_verts)
    return new_fp


def smooth_steps(footprint, smallest_ratio=0.2, num_steps=4) -> Polygon:
    l, verts = calculate_poly_side_length(footprint)
    if len(verts) <= 5:
        return footprint
    # make longest side first
    max_idx = np.argmax(l)
    verts = np.roll(verts, -max_idx, axis=0)
    l = np.roll(l, -max_idx)

    l_ratio = l / l.max()
    small_l = (l_ratio < smallest_ratio).astype(int)
    change = np.diff(small_l)
    change = np.insert(change, 0, 0)  # first wall is never small

    start_indices = np.where(change == 1)[0]  # going from big to small
    end_indices = np.where(change == -1)[0]  # going from small to big
    if len(start_indices) == 0 or len(end_indices) == 0:
        return footprint
    # If the array doesn't end with 0, append the length of the array to the end indices
    if end_indices[-1] < start_indices[-1]:
        end_indices = np.append(end_indices, len(small_l))

    print(start_indices)
    print(end_indices)
    step_lengths = end_indices - start_indices

    steps_start = (start_indices[step_lengths >= num_steps]) + 1
    steps_end = end_indices[step_lengths >= num_steps]

    if len(steps_start) == 0 or len(steps_end) == 0:
        return footprint
    for i in range(len(steps_start) - 1, -1, -1):
        verts = np.delete(verts, slice(steps_start[i], steps_end[i]), axis=0)
    if len(verts) < 4:
        return footprint
    new_fp = Polygon(verts)

    return new_fp
