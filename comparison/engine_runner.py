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

import argparse
import sys
import traceback

from main import runComparer
from report_back import report_back

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='Run Comparison')
    parser.add_argument('--image-path', metavar='str', required=True, help='the image name (with path)')
    parser.add_argument('--basemap-path', metavar='str', required=True, help='the geojson basemap file')
    parser.add_argument('--output-path', metavar='str', required=True, help='the name of the output folder')
    parser.add_argument('--callback-url', metavar='str', help='a callback url, to inform of the status')
    parser.add_argument('--classname', metavar='str', required=True, help='the class that is compared')

    args, unknown_args = parser.parse_known_args()
    print(f"unknown args = {unknown_args}")

    # Exactly one terminal callback, for success and for every failure.
    try:
        output_file = runComparer(args.image_path, args.basemap_path, args.output_path, args.classname)
        delivered = report_back(args.callback_url, True, {
            "comparison-type": args.classname,
            "output_file": output_file,
        })
    except BaseException as e:
        delivered = report_back(args.callback_url, False, {
            "comparison-type": args.classname,
            "error": str(e),
            "traceback": traceback.format_exc()})
    # A non-zero exit lets the backend notice a failed or undelivered run.
    sys.exit(0 if delivered else 1)
