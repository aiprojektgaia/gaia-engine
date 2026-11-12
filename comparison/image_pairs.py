import limits
import numpy as np
import cv2


class ImagePairIterator:
    """Iterator to get cut-outs of all segments in the image pair"""

    def __init__(self, max_n, stats, **images):
        """
        Parameters
        ----------
        max_n : int
            number of object to iterate over
        stats : ndarray
            statistics for each label including bounding box and area
        images: dict containing
            union : ndarray
                the union between basemap and segmentation image
            basemap : ndarray
                the basemap image
            image: ndarray
                the segmentation result
        """
        for required in ['union', 'basemap', 'image']:
            if not required in images:
                raise TypeError(
                    f"argument '{required}' missing in call to ImagePairIterator constructor")

        # omitting the first background label
        self.current = 1
        self.max_n = max_n
        self.images = images
        self.stats = stats

    def __iter__(self):
        return self

    def __next__(self):
        """Get next element

        Returns
        -------
        bounding box : tuple(int) (x0,y0,x1,y1)
            x- and y-coordinate of the tof left and bottom-right corner
        basemap: ndarray
            cut out from the basemap image
        image: ndarray
            cut out from the segmentation image
        """
        if self.current > self.max_n:
            raise StopIteration

        x0, y0, x1, y1 = self.getBoundingBox(self.current)
        # get a cut out from each image
        cut_outs = {}
        for key, im in self.images.items():
            cut_outs[key] = self.cropImage(im, x0, y0, x1, y1)
        mask = cut_outs['union'] == self.current
        # keep only the segment correponding to the current id
        for key in ['basemap', 'image']:
            cut_outs[key][mask == 0] = 0
        self.current += 1
        return (x0, y0, x1, y1), cut_outs['basemap'], cut_outs['image']

    def cropImage(self, image, x0, y0, x1, y1):
        # Crop first, then copy only the crop (a full-frame copy per component
        # is quadratic on busy tiles).
        return image[y0:y1+1, x0:x1+1].copy()

    def getBoundingBox(self, id):
        """Returns the x- and y-coordinate of the top left and lower right corner of the bounding box"""
        x0 = self.stats[id, cv2.CC_STAT_LEFT]
        y0 = self.stats[id, cv2.CC_STAT_TOP]
        w = self.stats[id, cv2.CC_STAT_WIDTH]
        h = self.stats[id, cv2.CC_STAT_HEIGHT]
        x1 = x0 + w
        y1 = y0 + h
        return x0, y0, x1, y1


class Pair:
    """Pair of basemap images and segmentation images"""

    def __init__(self, basemapimage: np.ndarray, image: np.ndarray):
        """
        Parameters
        ----------
        basemapimage : ndarray
            the basemap image
        image : ndarrray
            the result from the segmentation that should be compared with the basemap
        """
        self.basemap = basemapimage
        self.image = image

        # the union of the image, is white where basemap and/or image is white
        self.union_image = self.union(basemapimage, image)
        # find all connected components of the image, each segment gets a unique number
        (num_labels, labels, stats) = self.getConnectedComponent(self.union_image)

        if num_labels > limits.MAX_COMPONENTS:
            raise ValueError(
                f"{num_labels} connected components, the limit is {limits.MAX_COMPONENTS}")
        self.number_of_objects = num_labels
        self.labels_union = labels
        self.stats = stats

    def union(self, img1: np.ndarray, img2: np.ndarray) -> np.ndarray:
        """Computes the union of two binary images"""
        return cv2.bitwise_or(img1, img2)

    def getConnectedComponent(self, img: np.ndarray) -> tuple[int, np.ndarray, np.ndarray]:
        """Computes the connected components labeled image of boolean image and also produces a statistics output for each label
        Parameters
        ----------
        img : ndarray
            the image to find the connected components in

        Returns
        -------
        num_labels: int
            the number of labels in the image
        labels: ndarray
            labeled image
        stats: ndarray
            statistic output for each label, including th background (label 0)
            Statistics contain x- and y-coordinates for the top left corner of the bounding box, width and height of the bounding box and the area of the segment

        """
        # Count first with the label-only call; per-component statistics and
        # centroids are only allocated once the count is known to be sane.
        num_labels, _ = cv2.connectedComponents(img, connectivity=4, ltype=cv2.CV_32S)
        if num_labels - 1 > limits.MAX_COMPONENTS:
            raise ValueError(
                f"{num_labels - 1} connected components, the limit is {limits.MAX_COMPONENTS}")
        (num_labels, labels, stats, _) = cv2.connectedComponentsWithStats(
            img, 4, cv2.CV_32S
        )   # 4 is the argument: connectivity
        return (num_labels, labels, stats)

    def __iter__(self):
        """Returns an iterator that iterates over the different segments in the union image"""
        return ImagePairIterator(self.number_of_objects-1, self.stats, basemap=self.basemap, image=self.image, union=self.labels_union)
