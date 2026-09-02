"""
Unit tests for Haversine distance calculation.
"""
import unittest
from src.utils.geo_utils import haversine_distance


class TestHaversineDistance(unittest.TestCase):

    def test_same_point(self):
        dist = haversine_distance(28.6139, 77.2090, 28.6139, 77.2090)
        self.assertAlmostEqual(dist, 0.0, places=3)

    def test_known_distance(self):
        # New Delhi (28.6139, 77.2090) to Bareilly (28.3896, 79.44014)
        dist = haversine_distance(28.6139, 77.2090, 28.3896, 79.44014)
        # Expected approximate distance is ~220-230 km
        self.assertTrue(200.0 < dist < 250.0, f"Distance {dist} out of expected range")

if __name__ == "__main__":
    unittest.main()
