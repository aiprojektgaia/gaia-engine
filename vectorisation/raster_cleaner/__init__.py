import numpy as np
import scipy.ndimage
import skimage as ski
from skimage import morphology
from math import ceil


def clean_mask(
    mask, smallest_mask, smallest_hole, gap_closure=0, pixel_size=1, sigma=1.0
):
    if sigma > 0:
        mask = clipped_gaussian_smoothing(mask, sigma=(sigma / pixel_size))
    if smallest_mask > 0:
        mask = remove_small_masks(mask, min_size=smallest_mask / (pixel_size**2))
    if smallest_hole > 0:
        mask = fill_small_holes(mask, min_size=smallest_hole / (pixel_size**2))
    if gap_closure > 0:
        ball_size = ceil(gap_closure / pixel_size)
        morphology.binary_closing(
            mask, morphology.disk(ball_size, decomposition="sequence"), out=mask
        )
    return mask


def remove_small_masks(mask_data, min_size=0):
    """Remove small objects from a binary mask.

    This function removes objects smaller than `min_size` from a binary mask by first inverting the mask,
    then labeling all contiguous regions in both the original and inverted masks. Small objects are removed from both,
    and the results are combined to produce the final mask.

    Args:
        mask_data (ndarray): A binary mask array where objects are identified by `True` (or 1) and the background is `False` (or 0).
        min_size (int, optional): The minimum size of objects to retain in the mask. Objects smaller than this will be removed.
                                  The default is 0, which means that no objects will be removed based on size.

    Returns:
        ndarray: The binary mask array with small objects removed.
    """
    if min_size <= 0:
        return mask_data
    inv_mask = 1 - mask_data
    objects = ski.measure.label(mask_data)
    inv_objects = ski.measure.label(inv_mask)

    mask_data = ski.morphology.remove_small_objects(objects, min_size=min_size)
    inv_mask = ski.morphology.remove_small_objects(inv_objects, min_size=min_size)
    inv_mask = inv_objects ^ inv_mask
    # return inv_mask.astype(bool)
    # inv_mask = 1 - inv_mask
    mask_data = np.logical_or(mask_data, inv_mask)
    return mask_data.astype(bool)


def fill_small_holes(mask_data, min_size=0):
    if min_size <= 0:
        return mask_data
    mask_data = ski.morphology.remove_small_holes(
        mask_data, area_threshold=min_size, out=mask_data
    )
    return mask_data


def binary_closing(mask_data, iterations=0):
    if iterations > 0:
        scipy.ndimage.binary_closing(mask_data, iterations=iterations, output=mask_data)
    return mask_data


def clipped_gaussian_smoothing(mask_data, sigma=1.0):
    mask_data[mask_data > 0] = 1
    mask_data = mask_data.astype(float)
    mask_data = scipy.ndimage.gaussian_filter(mask_data, sigma=sigma)
    mask_data = mask_data > 0.5
    return mask_data
