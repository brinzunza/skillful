# Tests for Two Sum Solution
import unittest
from two_sum import two_sum

class TestTwoSum(unittest.TestCase):
    def test_example_case(self):
        self.assertEqual(two_sum([2, 7, 11, 15], 9), [0, 1])

    def test_no_solution(self):
        self.assertIsNone(two_sum([1, 2, 3], 6))

if __name__ == '__main__':
    unittest.main()