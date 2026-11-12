# Image bitter

Will take the segmentation result, a grey scale image, and apply a confidence level (threshold) and return a bit map (1s and 0s).

Should it merge multiple images into one? maybe!

## Installation

EDIT: There are no 3.13.0 GDAL available for Windows atm. that's needed to fix GHSA-h9rh and GHSA-j3f5. Ignore that for now.

This project depends on Gdal, and it might be a bit complex if you are installing it in a Windows machine.
When searching for gdal in Windows, you might find the following link: https://gis.stackexchange.com/questions/475387/installing-gdal-for-python
The link it points to will fail (no longer valid), but the author (gohlke) has a repository with the necessary files: https://github.com/cgohlke/geospatial-wheels?tab=readme-ov-file
In that GitHub repository, just go to the Releases and get the latest gdal version for your Python version.

Note. I have added one Gdal wheels version in this repository, but only for python 3.10 (might not be what you are using).

To install it locally you can use the following command:

```shell
pip install .\gdal-wheel\GDAL-3.10.1-cp312-cp312-win_amd64.whl
```

*Note*, I installed it from the root path (I did not execute the command above but this one)
```shell
pip install .\GDAL-3.10.1-cp312-cp312-win_amd64.whl
```


## File structure

A description of what each of the files do:

* cortado.py - Helper file, has all the necessary functions to handle the segmentation images, to get information or adjust it.
* apply-confidence.py - Takes a folder with binary images (uses cortado.py) and converts them to a single binary image applying a confidence level.
* file-merger.py - Helper file, it takes a list of binary images, does a union on them and converts them to a single and larger binary image.
* double-shot.py - orchestrates the process of applying the confidence level to several images and then merging them into one.
* main.py - entry point, takes a single image and applies the confidence level to it. Probably will be removed.
* engine_runner.py - entry point to run different processes, such as apply-confidence, merge-bits (merges files into one), merge-bits-with-confidence (applies confidence per file and then merges the result into one file).


## Calling it from gaia-backend would look something like this:

To run all the processes as one step: action = merge-bits-with-confidence
```shell
python engine_runner.py --image-path \segmentation-output --output-path results --confidence-level 73 --max-confidence-value 127 --action merge-bits-with-confidence
```

To apply the confidence level to several images
```shell
python engine_runner.py --image-path \segmentation-output --output-path results\per-image --confidence-level 73 --max-confidence-value 127 --action apply-confidence    
```

Merge bit images into one big image
```shell
python engine_runner.py --image-path results\per-image --output-path results\per-image --action merge-bits    
```


Other  examples:
```shell
# to apply the confidence level to one image
python apply_confidence.py --image-path data/65715_1635.tif --output-path results/buildings --confidence-level 69 --max-confidence-value 127

# Converts the segmentation output image to a binary image
# Takes a folder with binary images (result from cortado) and converts them to a single and large binary image
python file_merger.py --image-path \segmentation-output

# Takes a folder with the results of the segmentation and converts them to several binary images
# and from them it generates a single and large binary image
python double-shot.py --image-path \segmentation-output --output-path results --confidence-level 73 --max-confidence-value 127 --enable-logging True
```
