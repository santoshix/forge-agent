from src.logic import average
import unittest
class Cases(unittest.TestCase):
    def test_empty(self): self.assertEqual(average([]), 0)
    def test_mean(self): self.assertEqual(average([2,4,6]), 4)
    def test_negative(self): self.assertEqual(average([-2,-4]), -3)
