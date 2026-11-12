import unittest


class TestSum(unittest.TestCase):
    def test_create_tile_boundaries(self):
        from usecase.create_tile_boundaries import create_tile_boundaries, apply_overlap
        from models.LayerInfo import BoundingBox

        bbox = BoundingBox(0, 0, 10, 10)
        tile_size = 5
        tile_boundaries = create_tile_boundaries(bbox, tile_size)
        assert len(tile_boundaries) == 4
        assert str(tile_boundaries[0]) == str(BoundingBox(0, 0, 5, 5))
        assert str(tile_boundaries[1]) == str(BoundingBox(0, 5, 5, 10))
        assert str(tile_boundaries[2]) == str(BoundingBox(5, 0, 10, 5))
        assert str(tile_boundaries[3]) == str(BoundingBox(5, 5, 10, 10))

        overlap_percentage = 10
        tile_boundaries = apply_overlap(tile_boundaries, tile_size, overlap_percentage)
        assert len(tile_boundaries) == 4
        assert str(tile_boundaries[0]) == str(BoundingBox(-0.5, -0.5, 5.5, 5.5))
        assert str(tile_boundaries[1]) == str(BoundingBox(-0.5, 4.5, 5.5, 10.5))
        assert str(tile_boundaries[2]) == str(BoundingBox(4.5, -0.5, 10.5, 5.5))
        assert str(tile_boundaries[3]) == str(BoundingBox(4.5, 4.5, 10.5, 10.5))


    def test_create_one_tile_boundary_with_big_values(self):
        from usecase.create_tile_boundaries import create_tile_boundaries, apply_overlap
        from models.LayerInfo import BoundingBox

        bbox = BoundingBox(142000,6393000,143000,6394000)
        tile_size = 1000
        tile_boundaries = create_tile_boundaries(bbox, tile_size)
        assert len(tile_boundaries) == 1
        assert str(tile_boundaries[0]) == str(BoundingBox(142000, 6393000, 143000, 6394000))

        overlap_percentage = 10
        tile_boundaries = apply_overlap(tile_boundaries, tile_size, overlap_percentage)
        assert len(tile_boundaries) == 1
        assert str(tile_boundaries[0]) == str(BoundingBox(141900.0, 6392900.0, 143100.0, 6394100.0))


    def test_create_four_tile_boundary_with_big_values(self):
        from usecase.create_tile_boundaries import create_tile_boundaries, apply_overlap
        from models.LayerInfo import BoundingBox

        bbox = BoundingBox(142000,6393000,143100,6394100)
        tile_size = 1000
        tile_boundaries = create_tile_boundaries(bbox, tile_size)
        assert len(tile_boundaries) == 4
        assert str(tile_boundaries[0]) == str(BoundingBox(142000, 6393000, 143000, 6394000))
        assert str(tile_boundaries[1]) == str(BoundingBox(142000, 6394000, 143000, 6395000))
        assert str(tile_boundaries[2]) == str(BoundingBox(143000, 6393000, 144000, 6394000))
        assert str(tile_boundaries[3]) == str(BoundingBox(143000, 6394000, 144000, 6395000))

        overlap_percentage = 10
        tile_boundaries = apply_overlap(tile_boundaries, tile_size, overlap_percentage)
        assert len(tile_boundaries) == 4
        assert str(tile_boundaries[0]) == str(BoundingBox(141900.0, 6392900.0, 143100.0, 6394100.0))
        assert str(tile_boundaries[1]) == str(BoundingBox(141900.0, 6393900.0, 143100.0, 6395100.0))
        assert str(tile_boundaries[2]) == str(BoundingBox(142900.0, 6392900.0, 144100.0, 6394100.0))
        assert str(tile_boundaries[3]) == str(BoundingBox(142900.0, 6393900.0, 144100.0, 6395100.0))

    def test_create_tile_boundary_with_big_values_and_small_ppm(self):
        from usecase.create_tile_boundaries import create_tile_boundaries, apply_overlap, get_tile_size_in_meters
        from models.LayerInfo import BoundingBox

        bbox = BoundingBox(142000,6393000,143000,6394000)
        ppm = 0.08
        tile_size_pixels = 1000
        tile_size = get_tile_size_in_meters(ppm, tile_size_pixels)
        tile_boundaries = create_tile_boundaries(bbox, tile_size)

        total_expected = 169  # diff of coordinates (lat) is 1000m => 1000m/80pm = 12.5 => 13 per side => 13*13

        assert len(tile_boundaries) == total_expected
        assert str(tile_boundaries[0]) == str(BoundingBox(142000, 6393000, 142080.0, 6393080.0))
        assert str(tile_boundaries[-1]) == str(BoundingBox(142960.0, 6393960.0, 143040.0, 6394040.0))

        overlap_percentage = 10
        tile_boundaries = apply_overlap(tile_boundaries, tile_size, overlap_percentage)
        assert len(tile_boundaries) == total_expected
        assert str(tile_boundaries[0]) == str(BoundingBox(141992.0, 6392992.0, 142088.0, 6393088.0))
        assert str(tile_boundaries[-1]) == str(BoundingBox(142952.0, 6393952.0, 143048.0, 6394048.0))

if __name__ == '__main__':
    unittest.main()