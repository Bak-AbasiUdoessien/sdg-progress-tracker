"""
Unit tests for trend.py.  Run from the project folder with:
    python -m unittest discover tests
"""

import sys                                      # lets us change where Python looks for modules
import unittest                                 # built-in testing framework
from pathlib import Path                        # file paths

sys.path.insert(0, str(Path(__file__).parent.parent))  # add the project folder so "import trend" works

from trend import assess, linear_fit            # the functions we are testing  # noqa: E402


class TestLinearFit(unittest.TestCase):         # a group of related tests
    def test_perfect_line(self):
        # Points on y = 2x + 1 should give exactly slope 2 and intercept 1.
        slope, intercept = linear_fit([0, 1, 2, 3], [1, 3, 5, 7])
        self.assertAlmostEqual(slope, 2.0)      # AlmostEqual tolerates tiny floating-point errors
        self.assertAlmostEqual(intercept, 1.0)

    def test_needs_two_points(self):
        with self.assertRaises(ValueError):     # passes only if a ValueError is raised inside the block
            linear_fit([2020], [50])


class TestAssess(unittest.TestCase):
    def test_rising_access_reaches_target(self):
        # +5 points per year from 70% in 2020 -> passes 100% before 2030.
        result = assess([2020, 2021, 2022], [70, 75, 80], target=100, higher_is_better=True)
        self.assertTrue(result["on_track"])
        self.assertEqual(result["projected_2030"], 100.0)   # clamped at 100%

    def test_falling_poverty_too_slow(self):
        # Poverty falls only 0.5 points a year from 40% -> nowhere near 3% by 2030.
        result = assess([2018, 2019, 2020], [41, 40.5, 40], target=3, higher_is_better=False)
        self.assertFalse(result["on_track"])
        self.assertGreater(result["years_to_target"], 10)

    def test_wrong_direction_has_no_eta(self):
        # Getting worse -> years_to_target must be None.
        result = assess([2018, 2019, 2020], [60, 58, 56], target=100, higher_is_better=True)
        self.assertIsNone(result["years_to_target"])


if __name__ == "__main__":
    unittest.main()                             # run the tests when the file is executed directly
