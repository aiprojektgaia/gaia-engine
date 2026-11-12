import argparse
import traceback
from pathlib import Path
from apply_confidence import apply_confidence_to_all_files
from cortado import get_image_resolution
from helpers.report_back import report_back
from file_merger import merge_files

from helpers.logger import enable_logging, log, log_error

'''
# From segmentation results to a single binary file:

This file will take several segmentation result files, apply a confidence level to each one of then
and finally combine them into one.
The result will be the input for the vectorization process.
'''

def run_for_all_files(input_path: Path, output_path: Path,
                      confidence_level: int, max_confidence_value: int) -> str:

    # create a working area for the files in the output path
    working_area = output_path / "working_area"
    working_area.mkdir(parents=True, exist_ok=True)

    output_files = apply_confidence_to_all_files(input_path, working_area, confidence_level, max_confidence_value)

    dx, dy = get_image_resolution(output_files[0])
    log(f"dx: {dx}, dy: {dy}")

    merged_file = merge_files(output_files, output_path, dx, dy)

    # return the last file
    return merged_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog = 'Run Inference')
    parser.add_argument('--image-path', type=str, help='the image name (with path)')
    parser.add_argument('--output-path', type=str, help='the name of the output folder')
    parser.add_argument('--callback-url', type=str, help='a callback url, to inform of the status')
    parser.add_argument('--confidence-level', type=int, help='the threshold value, as a percentage, used to make a bit-value set as useful or not')
    parser.add_argument('--max-confidence-value', type=int, default=255, help='the max value bit can have. The default value is 255')
    parser.add_argument('--enable-logging', type=bool, default=False, help='enable only for debugging purposes')

    args, unknown_args = parser.parse_known_args()
    # log(f"unknown args = {unknown_args}")

    try:
        if args.enable_logging is True:
            enable_logging()

        output_file = run_for_all_files(Path(args.image_path), Path(args.output_path), args.confidence_level, args.max_confidence_value)
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
