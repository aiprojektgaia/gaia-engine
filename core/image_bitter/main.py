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
from apply_confidence import apply_confidence_to_all_files
from helpers.report_back import report_back

from helpers.logger import enable_logging, log, log_error

'''
This is just apply_confidence main part. Use engine_runner.py for all the options
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog = 'Run Inference')
    parser.add_argument('--image-path', type=str, help='the image name (with path)')
    parser.add_argument('--output-path', type=str, help='the name of the output folder')
    parser.add_argument('--callback-url', type=str, help='a callback url, to inform of the status')
    parser.add_argument('--confidence-level', type=int, help='the threshold value, as a percentage, used to make a bit-value set as useful or not')
    parser.add_argument('--max-confidence-value', type=int, default=255, help='the max value bit can have. The default value is 255')
    parser.add_argument('--enable-logging', type=bool, default=False, help='enable only for debugging purposes')

    args, unknown_args = parser.parse_known_args()
    # print(f"unknown args = {unknown_args}")

    try:
        if args.enable_logging is True:
            enable_logging()

        output_file = apply_confidence_to_all_files(Path(args.image_path), Path(args.output_path),
                                                     args.confidence_level, args.max_confidence_value)
        log(f"output_file = {output_file}")
        report_back(args.callback_url, True, {
            "confidence-level": args.confidence_level,
            "output_file": output_file
        })
    except Exception as e:
        log_error(e, traceback.format_exc())
        report_back(args.callback_url, False, {
            "confidence-level": args.confidence_level,
            "error": str(e),
            "traceback": traceback.format_exc()})
