import unittest
from src.exposure import Regimen, concentration

class ExposureTests(unittest.TestCase):
    def test_half_life(self):
        regimen = Regimen(100, 10, 4, 12, 1)
        self.assertAlmostEqual(concentration(regimen, 4), 5)

    def test_dose_boundary(self):
        regimen = Regimen(100, 10, 4, 8, 2)
        self.assertAlmostEqual(concentration(regimen, 8), 12.5)
        self.assertLess(concentration(regimen, 8 - 1e-6), 2.501)

    def test_finite_course(self):
        self.assertAlmostEqual(concentration(Regimen(100, 10, 4, 8, 2), 16), 3.125)

    def test_refuse_invalid_inputs(self):
        for value in [0, -1, float("inf"), float("nan")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                Regimen(100, 10, value, 8, 2)
        with self.assertRaises(ValueError):
            Regimen(100, 10, 4, 8, 1.5)
        with self.assertRaises(ValueError):
            concentration(Regimen(100, 10, 4, 8, 1), -1)

if __name__ == "__main__":
    unittest.main()
