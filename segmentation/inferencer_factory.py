from resunet_inferencer import ResUNetInferencer
import parameters

inferencers = {'resunet': ResUNetInferencer}

def getInferenceModel(classname,**kwargs):
    model_type,model_name,params = parameters.model(classname)
    for key in kwargs:
        if not key in params:
            raise ValueError(f"'{key}' is not a valid argument for a '{model_type}' inferencer")
        params[key] = kwargs[key]
    return inferencers[model_type](model_name,**params)