from enum import Enum
import numpy as np
from geo_object import getObjects
from image_object import ImageDrawer


class Comparer:
    """Base class to compare basemap building with segment"""
    class Case(Enum):
        SAME_BUILDING = 1
        ADDED = 2
        REMOVED = 3
        PARTIAL_ADDED = 4
        PARTIAL_REMOVED = 5
        UNKNOWN = 6
        NEW_ROAD = 10

    def __init__(self):
        raise NotImplementedError

    def compare(self, basemap_image: "np.ndarray", image: "np.ndarray") -> Case:
        raise NotImplementedError


class TileComparer:
    """Base class to compare a segmented tile to the basemap"""

    def __init__(self):
        raise NotImplementedError

    def compare(self, basemap: str, image: "np.ndarray", geodata: dict) -> "np.ndarray":
        # def compare(self,basemap_image:"np.ndarray", image: "np.ndarray") -> Case:
        raise NotImplementedError

    def createBasemapImage(self, size: tuple[int], basemap: str, geodata: dict) -> np.ndarray:
        """Create a binary mask from the list of polygons in the geojson file

        Parameters
        ----------
        size : tuple[int]
            desired size of the image (width,height)
        basemap : str
            filename or geojsonstring containing the basemap objects
        geodata : dict
           geograpical information about the image, should contain the fields dx, xrot, xo, dy, yrot, y0

        Returns
        -------
        np.ndarray
            binary mask showing the basemap objects
        """
        basemap_image = ImageDrawer(size, geodata)
        bounding_box = basemap_image.getWorldBoundingBox()
        # get the objects in te basemp as a list of GeoObjects
        objects = getObjects(basemap,bounding_box)
        for obj in objects:
            basemap_image.drawObject(obj)
        self.basemap_image = basemap_image.image
        return basemap_image.image
