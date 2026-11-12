import json

class LayerProperties:
    def __init__(self, min_area: int, smallest_hole: int, shortest_edge: float,
                 sigma: float,
                 smoothing: str,
                 simplify: str, simplify_tolerance: float,
                 vectorizer: str | None = None, gap_closure: int = 0,
                 subdivide: int = 0, smoothing_parameter: int = 0,):
        self.min_area = min_area
        self.smallest_hole = smallest_hole
        self.shortest_edge = shortest_edge
        self.sigma = sigma
        self.gap_closure = gap_closure
        self.vectorizer = vectorizer
        self.smoothing = smoothing
        self.subdivide = subdivide
        self.smoothing_parameter = smoothing_parameter
        self.simplify = simplify
        self.simplify_tolerance = simplify_tolerance

    def apply_smoothing(self):
        return self.smoothing and self.smoothing.lower() != "none"

    def __str__(self):
        return f"min_area: {self.min_area}, min_hole: {self.smallest_hole}, shortest_edge: {self.shortest_edge}, sigma: {self.sigma}, gap_closure: {self.gap_closure}, vectorizer: {self.vectorizer}, smoothing: {self.smoothing}, subdivide: {self.subdivide}, smoothing_parameter: {self.smoothing_parameter}"

def get_config(path: str):
    with open(path, "r") as f:
        config = json.load(f)
        return config


def get_layer_properties(config: dict, layer: str) -> LayerProperties:
    layer_prop_as_json = config["layer_properties"][layer]
    return LayerProperties(**layer_prop_as_json)