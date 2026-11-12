import limits
from comparer import TileComparer
import numpy as np
from enum import Enum
from image_pairs import Pair
from geo_object import getObjects
from image_object import ImageDrawer


class EdgeCase(Enum):
    EDGE = 100


class BuildingTileComparer(TileComparer):
    """Compare buildings in image tiles containing several buildings"""
    name = "building tile comparer"

    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        comparer : Comparer
            comparer type to use for comparing individual buildings
        kwargs: dict
            parameters to pass through to comparer
        """
        if 'comparer' not in kwargs:
            raise RuntimeError('No segment comparer were specified')
        comparer = kwargs.pop('comparer')
        self.comparer = comparer(**kwargs)

    def compare(self, basemap: str, image: np.ndarray, geodata: dict) -> np.ndarray:
        """ Compare basemap with segmentation result

        Parameters
        ----------
        basemap : str
            filename or geojsonstring containing the building objects
        image : ndarray
            image to compare with basemap
        geodata : dict
            geograpical information about the image, should contain the fields dx, xrot, xo, dy, yrot, y0

        Returns
        -------
        ndarray
            labeled image
        """
        basemap_image = self.createBasemapImage(
            (image.shape[1], image.shape[0]), basemap, geodata)
        result_image = self.compareImages(basemap_image, image)
        result_image = self.detectRemovedBuildings(result_image, image, basemap, geodata)
        return result_image

    def compareImages(self, basemap_image: np.ndarray, image: np.ndarray) -> np.ndarray:
        """ Compare basemap image with segmentation result

        Parameters
        ----------
        basemap : ndarray
            basemap image
        image : ndarray
            image to compare with basemap image

        Returns
        -------
        ndarray
            labeled image
        """
        pairs = Pair(basemap_image, image)
        result_image = np.zeros_like(image, dtype=np.uint8)

        for bbox, basemap_image_small, image_small in pairs:
            # check if builing is on image edge
            if self.onImageEdge(bbox, (result_image.shape[1], result_image.shape[0])):
                result = EdgeCase.EDGE
            else:
                # compare the individual buildings
                result = self.comparer.compare(
                    basemap_image_small, image_small)

            # updating the result image, if the segmentation image is empy, use the segment from basemap, otherwise from the segmentation
            if result == EdgeCase.EDGE:
                if np.sum(result_image) == 0:
                    result_image = self.updateResult(
                        result_image, basemap_image_small, bbox, result.value)
                else:
                    result_image = self.updateResult(
                        result_image, image_small, bbox, result.value)
            elif result == self.comparer.Case.REMOVED:
                result_image = self.updateResult(
                    result_image, basemap_image_small, bbox, result.value)
            else:
                result_image = self.updateResult(
                    result_image, image_small, bbox, result.value)

        return result_image

    def detectRemovedBuildings(self, result_image: np.ndarray, image: np.ndarray, basemap: str, geodata: dict) -> np.ndarray:
        """Per-polygon pass to detect removed buildings.

        Buildings that are close together merge into a single connected component
        in the union image, so the component-based comparison misses buildings
        that have no segmentation pixels but whose neighbours do.  This method
        iterates over each GeoJSON polygon individually and labels it REMOVED
        whenever its segmentation coverage is below the noise tolerance.
        """
        size = (image.shape[1], image.shape[0])
        drawer_ref = ImageDrawer(size, geodata)
        objects = getObjects(basemap, drawer_ref.getWorldBoundingBox())
        if len(objects) > limits.MAX_FEATURES:
            raise ValueError(
                f"{len(objects)} basemap features, the limit is {limits.MAX_FEATURES}")
        noise_tolerance = 1.0 - self.comparer.params['ratio']

        width, height = size
        rasterized = 0
        for obj in objects:
            # Draw each polygon only into the crop of its own pixel bounding
            # box (clipped to the tile) instead of a full-frame float image:
            # the work is proportional to the polygon, not to the tile.
            points = drawer_ref.toPixelIntegerCoordinates(obj.coords)
            cx0 = max(int(points[:, 0].min()), 0)
            cy0 = max(int(points[:, 1].min()), 0)
            cx1 = min(int(points[:, 0].max()), width - 1)
            cy1 = min(int(points[:, 1].max()), height - 1)
            if cx0 > cx1 or cy0 > cy1:
                continue  # entirely outside the tile
            rasterized += (cx1 - cx0 + 1) * (cy1 - cy0 + 1)
            if rasterized > limits.MAX_RASTERIZED_PIXELS:
                raise ValueError("basemap polygons exceed the rasterisation budget")
            crop = np.zeros((cy1 - cy0 + 1, cx1 - cx0 + 1), dtype=np.uint8)
            obj.draw(crop, points - np.array([cx0, cy0], dtype=points.dtype))

            if not crop.any():
                continue

            ys, xs = np.nonzero(crop)
            x0, y0 = int(xs.min()) + cx0, int(ys.min()) + cy0
            x1, y1 = int(xs.max()) + cx0, int(ys.max()) + cy0

            # skip buildings touching the tile boundary
            if self.onImageEdge((x0, y0, x1 + 1, y1 + 1), size):
                continue

            basemap_crop = crop[y0 - cy0:y1 - cy0 + 1, x0 - cx0:x1 - cx0 + 1]
            seg_crop = image[y0:y1 + 1, x0:x1 + 1].copy()
            seg_crop[basemap_crop == 0] = 0  # mask to polygon footprint

            basemap_px = int(np.sum(basemap_crop > 0))
            seg_px = int(np.sum(seg_crop > 0))

            if basemap_px > 0 and seg_px < noise_tolerance * basemap_px:
                result_image = self.updateResult(
                    result_image, basemap_crop, (x0, y0, x1, y1),
                    self.comparer.Case.REMOVED.value)

        return result_image

    def onImageEdge(self, bbox, image_size):
        """Detect if a bounding box if at the edge of the image"""
        (w, h) = image_size
        if bbox[0] == 0:
            return True
        if bbox[1] == 0:
            return True
        if bbox[2] == w:
            return True
        if bbox[3] == h:
            return True
        return False

    def updateResult(self, big_image, small_mask, mask_bounding_box, value):
        """Paste the result in the big image"""
        x0, y0, x1, y1 = mask_bounding_box
        cut_out = big_image[y0:y1+1, x0:x1+1]
        cut_out[small_mask > 0] = value
        big_image[y0:y1+1, x0:x1+1] = cut_out
        return big_image
