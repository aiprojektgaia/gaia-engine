import numpy as np
import cv2
from numpy.typing import ArrayLike
from typing import Union, Tuple


class ImageDrawer:
    """Class to draw GeoObjects on an image"""

    def __init__(self, size: tuple[int], geodata: dict):
        """
        Parameters
        ----------
        size : tuple[int]
            desired image size (width,height)
        geodata : dict
            geographic information for the image, should have fields dx, xrot, x0, dy, yrot and y0
        """
        self.size = size
        self.im = np.zeros((self.size[1], self.size[0]))
        self.geodata = geodata

    # TODO: also consider rotation
    def toPixelCoordinates(self, x: Union[float, ArrayLike], y: Union[float, ArrayLike] = None) -> Union[Tuple[np.ndarray[float]], np.ndarray[float]]:
        """Transforms world coordinats to pixel coordinates
        Parameters
        ----------
        x : float or one- or two-dimensional array-like
            x-coordinate of point(s) or array with both x- and y-coordinates
        y : float or one-dimensional array-like (optional)
            y-coordinate of point(s)

        Returns
        -------
        tuple(np.ndarray,np.ndarray) or np.ndarray
            the pixel coordinates, returns tuple with x- and y-coordinates if both was specified in the call, otherwise a two-dimensional array with both x- and y-coordinates

        """
        assert self.geodata['xrot'] == 0 and self.geodata['yrot'] == 0, "xrot != 0 and yrot != 0 is currently not supported"
        x = np.array(x)
        if not y is None:
            y = np.array(y)
            px = (x-self.geodata['x0'])/self.geodata['dx']
            py = (y-self.geodata['y0'])/self.geodata['dy']
            return px, py
        x0 = np.array([self.geodata['x0'], self.geodata['y0']])
        dx = np.array([self.geodata['dx'], self.geodata['dy']])
        return (x-x0)/dx

    def toPixelIntegerCoordinates(self, x: Union[float, ArrayLike], y: Union[float, ArrayLike] = None) -> Union[Tuple[np.ndarray[int]], np.ndarray[int]]:
        """Transforms world coordinats to pixel coordinates, rounded to closest integer
        Parameters
        ----------
        x : float or one- or two-dimensional array-like
            x-coordinate of point(s) or array with both x- and y-coordinates
        y : float or one-dimensional array-like (optional)
            y-coordinate of point(s)

        Returns
        -------
        tuple(np.ndarray,np.ndarray) or np.ndarray
            the pixel coordinates rounded to closest integer, returns tuple with x- and y-coordinates if both was specified in the call, otherwise a two-dimensional array with both x- and y-coordinates

        """
        if not y is None:
            px, py = self.toPixelCoordinates(x, y)
            return np.round(px).astype(np.int32), np.round(py).astype(np.int32)
        px = self.toPixelCoordinates(x)
        return np.round(px).astype(np.int32)

    def drawObject(self, obj):
        """Draw an object on the image
        Parameters
        ----------
        coords : two-dimensional array-like
            the coordinates for the vertices of the object
        """
        points = self.toPixelIntegerCoordinates(obj.coords)
        obj.draw(self.im,points)
    
    def getWorldBoundingBox(self) -> Tuple[float]:
        """Retruns the world bounding box of the image

        Returns
        -------
        Tuple[float]
            (xmin,ymin,xmax,ymax) the world coordinates of the upper left and lower right corner of the image
        """
        # pixel coordinates of the upper left and lower right cornerof the image
        px = np.array((0,self.size[0]))
        py = np.array((0,self.size[1]))
        # transform to world coordinates
        x = self.geodata['dx']*px + self.geodata['xrot']*py + self.geodata['x0']
        y = self.geodata['yrot']*px + self.geodata['dy']*py + self.geodata['y0']
        return (min(x[0],x[1]), min(y[0],y[1]), max(x[0],x[1]), max(y[0],y[1]))

    @property
    def image(self):
        """Returns the image"""
        return np.uint8(self.im)
