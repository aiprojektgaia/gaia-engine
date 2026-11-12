import math
import os

import cv2
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import numpy as np

MAX_RESIZED_SIDE = int(os.environ.get("GAIA_SEGMENT_MAX_SIDE", 16384))
MAX_RESIZED_PIXELS = int(os.environ.get("GAIA_SEGMENT_MAX_PIXELS", 100_000_000))


class Inferencer:
    """Base class to perform inference on an image tile"""

    def __init__(self):
        raise NotImplementedError

    def predict(self):
        raise NotImplementedError
    
    def resizeImageToTargetResolution(self, image: "np.ndarray", image_resolution: float, target_resolution: float, multiple_of: int = 1) -> "np.ndarray":
        """Rescale image to a multiple of n pixels and to desired resolution
        Parameters
        ----------
        image : np.ndarray
            image to resize
        image_resolution : float
            the resolution of the input image in m/pixel
        target_resolution : float
            the resolution of the target image in m/pixel
        multiple_of : int
            the number the image with and height should be divisible by

        Returns
        -------
        np.ndarray
            resized image
        """
        #get original image size and scaling factor
        (height, width) = image.shape[:2]
        # Resolution comes from untrusted raster metadata: validate it and
        # bound the output size before cv2 allocates anything.
        if not (math.isfinite(image_resolution) and math.isfinite(target_resolution)
                and image_resolution > 0 and target_resolution > 0):
            raise ValueError("image and target resolution must be finite and positive")
        scaling_factor = image_resolution/target_resolution
        new_height = height*scaling_factor
        new_width = width*scaling_factor
        if (new_height < max(multiple_of, 1) or new_width < max(multiple_of, 1)
                or new_height > MAX_RESIZED_SIDE or new_width > MAX_RESIZED_SIDE
                or new_height * new_width > MAX_RESIZED_PIXELS):
            raise ValueError(
                f"resized image {new_width:.0f}x{new_height:.0f} is outside the allowed size")
        #rescale image to a multiple of 32 pixels
        new_height = int(new_height - new_height % multiple_of)
        new_width = int(new_width - new_width % multiple_of)
        re_img = cv2.resize(image, (new_width, new_height),
                            interpolation=cv2.INTER_AREA)
        return re_img