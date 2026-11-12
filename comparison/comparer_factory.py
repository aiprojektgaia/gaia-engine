from comparer_v1 import ComparerV1
from building_tile_comparer import BuildingTileComparer
from road_tile_comparer import RoadTileComparer
import parameters

tile_comparers = {'building tile comparer': BuildingTileComparer,
                  'road tile comparer': RoadTileComparer}
comparers = {'comparer_v1': ComparerV1}


def getComparer(classname:str, **kwargs):
    """Returns comparer for a given class, which comparer to return is specified in 'parameters.json'

    Parameters
    ----------
    classname : str
        class to compare (for example buildings, roads etc.)
    kwargs : dict
        comparer-specific parameters

    Returns
    -------
    Comparer
        the defaul comparer for the given class

    Raises
    ------
    ValueError
        raise eror if non-valid argument were specified
    """
    (tile_model, tile_params, image_threshold), (seg_model,
                                seg_params) = parameters.comparerModel(classname)
    for key in kwargs:
        if key in tile_params:
            tile_params[key] = kwargs[key]
        elif key in seg_params:
            seg_params[key] = kwargs[key]
        else:
            if seg_model is None:
                raise ValueError(
                f"'{key}' is not a valid argument for a '{tile_model}' tile comparer")
            raise ValueError(
                f"'{key}' is not a valid argument for a '{tile_model}' tile comparer or a '{seg_model}' segment comparer")
    if seg_model is not None:
        return tile_comparers[tile_model](comparer = comparers[seg_model], **tile_params, **seg_params), image_threshold
    return tile_comparers[tile_model](**tile_params), image_threshold
