import argparse
import traceback
from pathlib import Path
import raster_limits
from cortado import read_image, apply_confidence_level, create_bitmap_file
from helpers.report_back import report_back
from helpers.logger import log, log_error


def apply_confidence_to_all_files(input_path: Path, output_path: Path,
                      confidence_level: int, max_confidence_value: int) -> list[str]:
    # get all files
    files = list(input_path.glob("*.tif"))
    log(files)
    raster_limits.check_file_count(files)
    for f in files:
        raster_limits.check_file_size(f)
    # run process per file and store output
    output_files = []
    for file in files:
        processed_file = apply_confidence_level_to_file(file, output_path, confidence_level, max_confidence_value)
        output_files.append(processed_file)

    # return the last file
    return output_files

def apply_confidence_level_to_file(image_path: Path, output_path: Path,
                confidence_level: int, max_confidence_value: int ) -> str:
    # get the file
    # get band #1
    log(f"image to read: {image_path}")
    band_one, transform, profile = read_image(image_path)
    log(f"shape: {band_one.shape}")
    #log(f"transform-a: {transform.a}")

    confidence_value = (confidence_level / 100) * max_confidence_value
    log(f"conf-level:{confidence_level}, max_confidence_value: {max_confidence_value}")
    log(f"min confidence_value: {confidence_value}")
    # apply confidence_level and create a bitmap file out of it
    bitter_array = apply_confidence_level(band_one, confidence_value)
    # write it out
    file_name = image_path.name
    created_file = create_bitmap_file(bitter_array, profile, f"bit_{file_name}", output_path)
    # return new image
    log(created_file.name)
    return str(created_file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog = 'Run Inference')
    parser.add_argument('--image-path', type=str, help='the image name (with path)')
    parser.add_argument('--output-path', type=str, help='the name of the output folder')
    parser.add_argument('--callback-url', type=str, help='a callback url, to inform of the status')
    parser.add_argument('--confidence-level', type=int, help='the threshold value, as a percentage, used to make a bit-value set as useful or not')
    parser.add_argument('--max-confidence-value', type=int, default=255, help='the max value bit can have. The default value is 255')

    args, unknown_args = parser.parse_known_args()
    # log(f"unknown args = {unknown_args}")

    try:
        output_file = apply_confidence_level_to_file(Path(args.image_path), Path(args.output_path),
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
