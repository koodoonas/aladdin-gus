import unittest

from tools.patch_aladdin_gus import build_sound_cfg, parse_ultrasnd


class UltrasndTests(unittest.TestCase):
    def test_standard_shared_resources(self):
        self.assertEqual(parse_ultrasnd("240,7,7,7,7"), (0x240, 7, 7, 7, 7))

    def test_separate_resources(self):
        cfg = build_sound_cfg("250,5,6,11,12")
        self.assertEqual(len(cfg), 54)
        self.assertEqual(cfg[0], 10)
        self.assertEqual(cfg[0x23:0x25], bytes((0x50, 0x02)))
        self.assertEqual(cfg[0x25], 11)
        self.assertEqual(cfg[0x26], 5)
        self.assertEqual(cfg[0x2E], 6)
        self.assertEqual(cfg[0x2F], 12)
        self.assertEqual(cfg[0x30:0x32], bytes((1, 1)))

    def test_invalid_dma_four(self):
        with self.assertRaises(ValueError):
            parse_ultrasnd("240,4,7,7,7")

    def test_invalid_shape(self):
        with self.assertRaises(ValueError):
            parse_ultrasnd("240,7,7")


if __name__ == "__main__":
    unittest.main()
