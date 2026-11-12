import limits
from comparer import TileComparer, Comparer
import numpy as np
import cv2


class RoadTileComparer(TileComparer, Comparer):
    """Compare tile with roads with basemap where roads in basemap is represented by lines"""
    name = "road tile comparer"

    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        dist : int
            margin around each line in the basemap in meters, default is 8 m
        min_length : float
            shortest road to accept as a new road, default is 30 m
        """
        self.params = {'dist': 8,
                       'min_length': 30}
        # updating parameters if specified in the call
        for key in kwargs:
            if not key in self.params:
                raise ValueError(f"{key} is not a valid argument")
            self.params[key] = kwargs[key]

    def compare(self, basemap: str, image: np.ndarray, geodata: dict) -> np.ndarray:
        """ Compare basemap with segmentation result

        Parameters
        ----------
        basemap : str
            filename or geojsonstring containing the road lines
        image : ndarray
            image to compare with basemap
        geodata : dict
            geograpical information about the image, should contain the fields dx, xrot, xo, dy, yrot, y0

        Returns
        -------
        ndarray
            labeled image
        """
        xresolution = np.sqrt(geodata['dx']**2 + geodata['yrot']**2)
        yresolution = np.sqrt(geodata['xrot']**2 + geodata['dy']**2)
        resolution = (xresolution + yresolution)/2
        limits.check_resolution(float(resolution))
        limits.check_kernel(int(2*self.params['dist']/resolution) + 1)
        self.dist = int(self.params['dist']/resolution)
        self.min_length = self.params['min_length']/resolution
        basemap_image = self.createBasemapImage(
            (image.shape[1], image.shape[0]), basemap, geodata)
        return self.compareImages(basemap_image, image)

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
        result_image = np.zeros_like(image)
        new_roads = self.findNewRoads(basemap_image, image)
        result_image[new_roads > 0] = self.Case.NEW_ROAD.value
        return result_image

    def findNewRoads(self, basemap_image: np.ndarray, segmented_image: np.ndarray) -> np.ndarray:
        """Find roads that is present in the orthophoto but not in the basemap

        Parameters
        ----------
        basemap_image : np.ndarray
            basemap image
        segmented_image : np.ndarray
            image to compare with basemap image

        Returns
        -------
        np.ndarray
            image with only new roads
        """
        road_edges = self.findEdges(segmented_image)
        difference = self.findDifferences(
            road_edges, basemap_image, self.dist)
        thin_difference = self.thinnenImage(difference)

        large_difference = self.removeSmallDifferences(thin_difference)
        kernel_size = 2*self.dist
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        new_roads = cv2.bitwise_and(cv2.dilate(
            large_difference, kernel), segmented_image)
        return new_roads

    def findEdges(self, image: np.ndarray) -> np.ndarray:
        """Find segment edges

        Parameters
        ----------
        image : np.ndarray
            binary image

        Returns
        -------
        np.ndarray
            binary image with the border of the segments
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        return cv2.morphologyEx(image, cv2.MORPH_GRADIENT, kernel)

    def thinnenImage(self, image: np.ndarray) -> np.ndarray:
        """Skeletonize input image, reduces width of any segment to one pixel 

        Parameters
        ----------
        image : ndarray
            image to skeletonize

        Returns
        -------
        ndarray
            skeletonized image
        """
        return cv2.ximgproc.thinning(image)

    def findDifferences(self, image: np.ndarray, image_to_subtract: np.ndarray, margin: int) -> np.ndarray:
        """Find pixels that is present in the first image but no in the second (with some margin)

        Parameters
        ----------
        image : np.ndarray
            first image, the image to find elements in
        image_to_subtract : np.ndarray
             image to subtract from first image
        margin : int
            the margin around each pixel to decide if the pixel is present in both images or not

        Returns
        -------
        np.ndarray
             image with roads that is not present in the basemap
        """
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (2*margin+1, 2*margin+1))
        dilated_image = cv2.dilate(image_to_subtract, kernel)
        difference = image.copy()
        difference[dilated_image > 0] = 0

        return difference

    def removeSmallDifferences(self, difference: np.ndarray) -> np.ndarray:
        """Remove roads shorter that a certain length given in the parameters of the tile comparer

        Parameters
        ----------
        difference : np.ndarray
            skeletonized image with roads

        Returns
        -------
        np.ndarray
            skeletonized image with roads longer than 'min dist' m
        """
        num_labels, _ = cv2.connectedComponents(difference, connectivity=8, ltype=cv2.CV_32S)
        if num_labels - 1 > limits.MAX_COMPONENTS:
            raise ValueError(
                f"{num_labels - 1} road components, the limit is {limits.MAX_COMPONENTS}")
        (num_labels, labels, stats, _) = cv2.connectedComponentsWithStats(
            difference, 8, cv2.CV_32S
        )

        # One lookup instead of a full-frame scan per label: keep[label] says
        # whether that component is long enough (label 0 is background).
        keep = stats[:, cv2.CC_STAT_AREA] >= self.min_length
        keep[0] = False
        large_difference = np.zeros_like(difference)
        large_difference[keep[labels]] = 255

        return large_difference
