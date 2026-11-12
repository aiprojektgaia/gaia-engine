
def readTfwFile(filename):
    with open(filename,'r') as f:
        data = f.read()
    lines = data.split('\n')
    return {'dx':float(lines[0]),
            'xrot':float(lines[1]),
            'yrot':float(lines[2]),
            'dy':float(lines[3]),
            'x0':float(lines[4]),
            'y0':float(lines[5])}

def parseGeoInfo(transform):
    return {'dx':transform[0],
            'xrot':transform[1],
            'x0':transform[2],
            'yrot':transform[3],
            'dy':transform[4],
            'y0':transform[5]}