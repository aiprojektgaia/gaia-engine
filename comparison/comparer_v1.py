from comparer import Comparer
import numpy as np
import cv2

class ComparerV1(Comparer):
    """Compare basemap building with the segmentation result for the same building with first version of comparison algorithm"""
    name = "comparer_v1"
    def __init__(self,**kwargs):
        """
        Parameters
        ----------
        threshold : floats
            threshold to use to decide if two images depicts the same building, default is 0.1, value should be between 0.0 and 1.0
        ratio : float
            ratio to use to determine if it is an extension or opposite if building differs, default is 0.90
        """
        self.params = {'threshold': 0.1,
                       'ratio': 0.90}
        #updating parameters if specified in the call
        for key in kwargs:
            if not key in self.params:
                raise ValueError(f"{key} is not a valid argument")
            self.params[key] = kwargs[key]

    def compare(self,basemap_image:"np.ndarray", image: "np.ndarray") -> Comparer.Case:
        """Compares two segments
        Parameters
        ----------
        basemap_image : np.ndarray
            the basemap image to compare with the segmentation
        image : np.ndarray
            the segmentation image to compare with the basemap image
        
        Returns
        -------
        enum 'Case'
            the result of the comparison as an enum element
        """
        #perfoms a series of comparisons to determine what have changed (if anything) 
        if self.isAdded(basemap_image, image):
            return self.Case.ADDED
        
        if self.isRemoved(basemap_image, image):
            return self.Case.REMOVED
        
        if self.isSameShape(basemap_image, image):
            return self.Case.SAME_BUILDING
        
        return self.overLayContours(basemap_image, image)

    def isAdded(self,basemap:np.ndarray, segment:np.ndarray) -> bool:
        """Check if there is a there is a segment in the segmentation image that is not present in the basemap image
        Parameters
        ----------
        basemap_image : np.ndarray
            the basemap image to compare with the segmentation
        image : np.ndarray
            the segmentation image to compare with the basemap image
        
        Returns
        -------
        bool
            True if a segment was added False otherwise
        """
        if np.max(segment) == 0:
            return False
        if np.max(basemap) == 0:
            return True
        noise_tolerance = 1 - self.params['ratio']
        return np.sum(basemap > 0) < noise_tolerance * np.sum(segment > 0)
    
    def isRemoved(self,basemap:np.ndarray, segment:np.ndarray)->bool:
        """Check if there is a there is a segment in the basemap image that is not present in the segmentation image
        Parameters
        ----------
        basemap_image : np.ndarray
            the basemap image to compare with the segmentation
        image : np.ndarray
            the segmentation image to compare with the basemap image
        
        Returns
        -------
        bool
            True if a segment was removed False otherwise
        """
        if np.max(basemap) == 0:
            return False
        if np.max(segment) == 0:
            return True
        noise_tolerance = 1 - self.params['ratio']
        return np.sum(segment > 0) < noise_tolerance * np.sum(basemap > 0)

    def isSameShape(self, basemap:np.ndarray, segment:np.ndarray)-> bool:
        """Check two segments have the same shape
        Parameters
        ----------
        basemap_image : np.ndarray
            the basemap image to compare with the segmentation
        image : np.ndarray
            the segmentation image to compare with the basemap image
        
        Returns
        -------
        bool
            True if the two segments have the same shape False otherwise
        """
        cons, _ = cv2.findContours(basemap, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cnt1 = cons[0]

        segmentSingle = self.fillPolyLargestContour(segment)
        cons, _ = cv2.findContours(segmentSingle, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if (len(cons) > 1):
            print(f"cons more than one")
        cnt2 = cons[0]
        value = cv2.matchShapes(cnt1, cnt2, 3, 0.0)   #3 is the match mode, if two equals, ret = 0.0
        if value <= self.params['threshold']:
            return True
        else:
            return False
    
    def overLayContours(self, basemap:np.ndarray, segment:np.ndarray) -> Comparer.Case:
        """Compares the two segments to the union of them to find partly added or removed buildings
        Parameters
        ----------
        basemap_image : np.ndarray
            the basemap image to compare with the segmentation
        image : np.ndarray
            the segmentation image to compare with the basemap image
        
        Returns
        -------
        enum 'Case'
            the result of the comparison as an enum element
        """
        assert basemap.shape == segment.shape, f"shape differ {basemap.shape}, {segment.shape}" 

        basemapNorm = (basemap > 0).astype(np.uint8)
        segmentNorm = (segment > 0).astype(np.uint8)

        overLay = np.logical_or(basemapNorm, segmentNorm).astype(np.uint8)

        if np.array_equal(basemapNorm, overLay):
            return self.Case.PARTIAL_REMOVED
        elif np.array_equal(segmentNorm, overLay):
            return self.Case.PARTIAL_ADDED
        elif self.isSameShape(basemap, overLay*255): # TODO make sure basemap has the correct format {0,255}
            result = self.compareAreaRatio(basemap, segment)
            return result
        return self.Case.UNKNOWN


    def fillPolyLargestContour(self,binary_img: np.ndarray) -> np.ndarray:
        """Kepp only the largest segment in the image
        Parameters
        ----------
        binary_img : np.ndarray
            the image to clean

        Returns
        -------
        np.ndarray
            the image with only one segment
        """
        cnts, _ = cv2.findContours(binary_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        cnt = sorted(cnts, key=cv2.contourArea)
        largest = cnt[-1]
        mask = np.zeros(binary_img.shape, dtype = np.uint8)
        cv2.fillPoly(mask, pts=[largest], color=255)

        return mask

    def compareAreaRatio(self,basemap:np.ndarray, segment:np.ndarray) -> Comparer.Case:
        assert basemap.shape == segment.shape, f"shape differ {basemap.shape}, {segment.shape}" 
        (height, width) = basemap.shape          
        norm_area_base = np.sum(basemap > 0) / (height * width)
        norm_area_segm = np.sum(segment > 0) / (height * width)
        seg_to_bas = norm_area_segm / norm_area_base
        bas_to_seg =  norm_area_base / norm_area_segm
        ratio = self.params['ratio']
        if seg_to_bas <= ratio:
            return self.Case.PARTIAL_REMOVED
        if bas_to_seg <= ratio:  
            return self.Case.PARTIAL_ADDED
        if (seg_to_bas >= ratio) and (seg_to_bas <= 1):
            return self.Case.SAME_BUILDING
        if (bas_to_seg >= ratio) and (bas_to_seg <= 1):
            return self.Case.SAME_BUILDING
        else:
            return self.Case.UNKNOWN
