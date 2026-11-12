# Copyright 2023-2026 The GAIA project contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from inferencer_factory import getInferenceModel
from utils import parseGeoInfo
from math import isfinite
from numpy import sqrt
import cv2
import os.path
import rasterio
import warnings
warnings.filterwarnings("error", category=rasterio.errors.NotGeoreferencedWarning)

MAX_INPUT_PIXELS = int(os.environ.get("GAIA_SEGMENT_MAX_INPUT_PIXELS", 100_000_000))

def runInference(image_name,output_folder,classname):
    #open image file and check for geo information
    try:
        with rasterio.open(image_name) as img:
            profile = img.profile
    except rasterio.errors.NotGeoreferencedWarning:
        raise ValueError("The input image does not have any geo reference information.")
    geodata = profile['transform']
    if profile['width'] * profile['height'] > MAX_INPUT_PIXELS:
        raise ValueError("The input image is larger than the allowed pixel limit.")
    image = cv2.imread(image_name)

    #read geo information and check that the resolution is square
    tfw_data = parseGeoInfo(geodata)
    xresolution = sqrt(tfw_data['dx']**2 + tfw_data['yrot']**2)
    yresolution = sqrt(tfw_data['xrot']**2 + tfw_data['dy']**2)
    # explicit checks (assert is stripped under -O); metadata is untrusted
    if not (isfinite(xresolution) and isfinite(yresolution)
            and xresolution > 0 and yresolution > 0):
        raise ValueError("the image resolution must be finite and positive")
    if abs(xresolution - yresolution) >= 1e-6:
        raise ValueError("x- and y- resolution must be the same")

    resolution = (xresolution + yresolution)/2

    #load the model and perform the inference
    model = getInferenceModel(classname)
    pred = model.predict(image,resolution)

    #save the result (with geo information)
    output_file_name = os.path.basename(image_name)
    target_file = f"{output_folder}/{output_file_name}"
    
    profile.update(count = 1)
    with rasterio.open(target_file, "w", **profile) as dest:
        dest.write(pred,indexes = 1)

    return target_file

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(prog = 'Run Inference')
    parser.add_argument('image', metavar='path', help='the imagename (with path)')
    parser.add_argument('output_folder', metavar='path',
                        help='the name of the output folder')
    parser.add_argument('classname', metavar='str', help='the class that should be segmented')
    args = parser.parse_args()
    runInference(args.image,args.output_folder,args.classname)