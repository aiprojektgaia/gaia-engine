import json


def readParametersFile():
    with open("parameters.json", "r") as f:
        data = json.load(f)
    return data


def comparerModel(classname):
    parameters = readParametersFile()
    models = parameters['models']
    tile_comparer = models[classname]["tile comparer"]
    tile_comparer_parameters = parameters["tile comparer"][tile_comparer]["parameters"]
    image_threshold = parameters["tile comparer"][tile_comparer].get("image_threshold", None)

    seg_comparer = models[classname]["segment comparer"]
    if seg_comparer is None:
        return (tile_comparer, tile_comparer_parameters, image_threshold),(None,{})
    seg_comparer_parameters = parameters["segment comparer"][seg_comparer]["parameters"]
    return (tile_comparer, tile_comparer_parameters, image_threshold), (seg_comparer, seg_comparer_parameters)
