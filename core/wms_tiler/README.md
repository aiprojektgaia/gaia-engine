# WMS Tiler documentation

This is a library which will connect to a wms service and download the tiles and save it in the local system. 
Most of the information has to be passed as arguments.

## Installation
```
    # To create local venv, be at the root of the project and run 
    python -m venv .venv
    
    # To install the requirements
    pip install -r requirements.txt
```

## Arguments list
* 'wms-server-url': 'a base wms url. eg: http://localhost:8080/geoserver/wms'
* 'layer-name': 'the wms layer name. eg: topp:states'
* 'tile-size': 'the height/width of the image in pixels. It is a square. eg: 1024'
* 'mpp': 'meters per pixel. eg: 0.08'
* 'overlap': 'a percentage of overlap between tiles. eg: 10'
* 'bbox': 'the bounding box for the area to be tiled. eg: topleft_x,topleft_y,bottomright_x,bottomright_y'
* 'epsg': 'the coordinates system of the bounding box. eg: EPSG:3006'
* 'output_path': 'the name of the output folder'
* 'image_format': 'the image format to be saved. eg: geotiff, png, tif'
* 'callback_url': 'a callback url, to inform of the status'

## example
```
    python main.py \
        --wms-server-url http://localhost:8080/geoserver/wms \
        --layer-name gaia:got \
        --ppm 0.08 \
        --tile-size 1000 \
        --overlap 10 \
        --bbox 11.0,57.0,25.0,66.0 \
        --epsg EPSG:3007 \
        --output-path output \
        --image-format geotiff \
        --callback-url http://localhost:8000/callback
```

Local to my computer example:
```
    python main.py
        --wms-server-url http://localhost:9600/geoserver/wms
        --layer-name gaia:GOT_6393_142
        --ppm 0.08
        --tile-size 1000
        --overlap 10
        --bbox "142000,6393000,143000,6394000"
        --epsg EPSG:3007
        --output-path "D:\Temp\gaia-tmp\wms_out"
        --image-format geotiff
        --callback-url http://localhost:8000/callback
        
 
    python main.py --wms-server-url http://localhost:9600/geoserver/wms --layer-name gaia:GOT_6393_142 --mpp 0.08 --tile-size 1000  --overlap 10 --bbox "142000,6394000,143000,6393000" --epsg EPSG:3007 --output-path  "D:\Temp\gaia-tmp\wms_out" --image-format geotiff --callback-url http://localhost:8000/callback
    
    # callback is not needed in case you run it from command line
    python main.py --wms-server-url http://localhost:9600/geoserver/wms --layer-name gaia:GOT_6393_142 --mpp 0.08192 --tile-size 1024  --overlap 10 --bbox "142000,6394000,143000,6393000" --epsg EPSG:3007 --output-path  "D:\Temp\gaia-tmp\wms_out" --image-format geotiff

```
