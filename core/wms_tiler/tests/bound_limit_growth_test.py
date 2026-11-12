import unittest

class TestGrowth(unittest.TestCase):

    def test_get_tile_size_in_meters(self):
        from usecase.create_tile_boundaries import get_tile_size_in_meters
        mpp = 0.1
        tile_size_in_pixels = 100
        assert get_tile_size_in_meters(mpp, tile_size_in_pixels) == 10.0

        mpp = 0.08
        tile_size_in_pixels = 100
        assert get_tile_size_in_meters(mpp, tile_size_in_pixels) == 8.0

    def test_get_unpadded_tile_size_in_meters(self):
        from usecase.create_tile_boundaries import get_unpadded_tile_size_in_meters
        tile_size_in_meters = 10
        overlap_percentage = 10
        assert get_unpadded_tile_size_in_meters(tile_size_in_meters, overlap_percentage) == 9.090909090909092
        # the formula is:
        # tile_size_in_meters  is (overlap_percentage + 100)% of the unpadded tile size
        #        x             is 100% of the unpadded tile size
        #
        # => x = 100 * tile_size_in_meters / (overlap_percentage + 100)

        assert get_unpadded_tile_size_in_meters(tile_size_in_meters, overlap_percentage) == 100 * tile_size_in_meters / (overlap_percentage + 100)

        tile_size_in_meters = 8
        overlap_percentage = 10
        assert get_unpadded_tile_size_in_meters(tile_size_in_meters, overlap_percentage) == 100 * tile_size_in_meters / (overlap_percentage + 100)

if __name__ == '__main__':
    unittest.main()
