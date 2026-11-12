import json

def readParametersFile():
    with open("parameters.json","r") as f:
        data = json.load(f)
    return data

def data_folder():
    return readParametersFile()['data folder']

def result_folder(classname):
    folders = readParametersFile()['result folder']
    if not classname in folders:
        raise ValueError(f"'{classname}' is not a valid class")
    return folders[classname]

def model(classname):
    models = readParametersFile()['models']
    if not classname in models:
        raise ValueError(f"'{classname}' is not a valid class")
    model = models[classname]
    mtype = model['model type']
    mname = model['model name']
    mparameters = model['parameters']
    return mtype,mname,mparameters