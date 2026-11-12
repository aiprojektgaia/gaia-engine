class BoundingBox:
    def __init__(self, min_x: float, min_y: float, max_x: float, max_y: float):
        self.min_x: float = min_x
        self.min_y: float = min_y
        self.max_x: float = max_x
        self.max_y: float = max_y

    def __str__(self):
        return f"({self.min_x}, {self.min_y}), ({self.max_x}, {self.max_y})"

class LayerInfo:
    def __init__(self, name: str, title: str, srs: str,
                 wgs84_bounding_box: BoundingBox,
                 bounding_box: BoundingBox):
        self.name: str = name
        self.title: str = title
        self.srs: str = srs
        self.wgs84_bounding_box: BoundingBox = wgs84_bounding_box
        self.bounding_box: BoundingBox = bounding_box
