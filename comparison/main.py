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

import limits
import rasterio
import cv2
import os.path
from comparer_factory import getComparer
from utils import parseGeoInfo
from geo_object import MAX_BASEMAP_BYTES
import warnings
warnings.filterwarnings("error", category=rasterio.errors.NotGeoreferencedWarning)

def runComparer(image_name,basemap,output_folder,classname):
    try:
        with rasterio.open(image_name) as img:
            profile = img.profile
    except rasterio.errors.NotGeoreferencedWarning:
        raise ValueError("The input image does not have any geo reference information.")
    geodata = profile['transform']
    # Check the declared size before decoding anything into memory.
    if profile['width'] * profile['height'] > limits.MAX_IMAGE_PIXELS:
        raise ValueError("The input image is larger than the allowed pixel limit.")
    image = cv2.imread(image_name,cv2.IMREAD_GRAYSCALE)
    limits.check_image(image)
    with open(basemap, 'r') as file:
        basemap_jsonstring = file.read(MAX_BASEMAP_BYTES + 1)
    if len(basemap_jsonstring) > MAX_BASEMAP_BYTES:
        raise ValueError('The basemap is larger than the allowed size.')

    tfw_data = parseGeoInfo(geodata)

    comparer, image_threshold = getComparer(classname)
    if image_threshold is not None:
        _, image = cv2.threshold(image, image_threshold, 255, cv2.THRESH_BINARY)
    result_image = comparer.compare(basemap_jsonstring,image,tfw_data)

    output_file_name = os.path.basename(image_name)
    target_file = f"{output_folder}/{output_file_name}"

    profile.update(count = 1)

    with rasterio.open(target_file, "w", **profile) as dest:
        dest.write(result_image,indexes = 1)

    return target_file

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(prog = 'Run Comparison')
    parser.add_argument('image', metavar='path', help='the full path to the imagename')
    parser.add_argument('basemap', metavar='path', help='the full path to basemap geojson file')
    parser.add_argument('output_folder', metavar='path',
                        help='the name of the output folder')
    parser.add_argument('classname', metavar='str', help='the class that should be segmented')
    args = parser.parse_args()
    runComparer(args.image,args.basemap,args.output_folder,args.classname)