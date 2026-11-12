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
import traceback
from pathlib import Path

from layer_types.generalized_type import start_process
from helpers.report_back import report_back


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog = 'Run Vectorization')
    parser.add_argument('--image-path', metavar='str',
                        help='the image name (with path)')
    parser.add_argument('--output-path', metavar='str',
                        help='the name of the output folder')
    parser.add_argument('--callback-url', metavar='str',
                        help='a callback url, to inform of the status')
    parser.add_argument('--classname', metavar='str',
                        help='the model class name it will run')

    args, unknown_args = parser.parse_known_args()
    print(f"unknown args = {unknown_args}")

    try:
        output_file = "unknown"
        supported_classes = ["buildings", "roads", "hard_surfaces", "vegetation"]

        if args.classname in supported_classes:
            output_file = start_process(args.classname, Path(args.image_path), Path(args.output_path))
        else:
            raise ValueError(f"The classname {args.classname} is not recognized or implemented")

        report_back(args.callback_url, True, {
            "vectorizing-type": args.classname,
            "output_file": output_file,
        })
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        report_back(args.callback_url, False, {
            "vectorizing-type": args.classname,
            "image_path": args.image_path,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
