"""高低列の復元と比較仕様のテスト。"""
import unittest
from pitch import from_kernel, from_codes, matching_pattern


class PitchTests(unittest.TestCase):
    def test_dictionary_patterns(self):
        self.assertEqual(from_kernel(5, 0), [1, 2, 2, 2, 2])
        self.assertEqual(from_kernel(5, 5), from_kernel(5, 0))
        self.assertEqual(from_kernel(5, 1), [2, 1, 1, 1, 1])
        self.assertEqual(from_kernel(5, 3), [1, 2, 2, 1, 1])

    def test_restore_initial_rise(self):
        self.assertEqual(from_codes([1, 1, 1, 1], 4), [1, 2, 2, 2])
        self.assertEqual(from_codes([0, 1, 1, 1], 4), [2, 1, 1, 1])

    def test_preserve_multiple_transitions(self):
        self.assertEqual(from_codes([1, 0, 2, 0, 1], 5), [1, 2, 1, 2, 1])
        self.assertEqual(from_codes([0, 2, 0, 1], 4), [2, 1, 2, 1])

    def test_terminal_fall_is_outside_word(self):
        self.assertEqual(from_codes([1, 1, 1, 0], 4), from_codes([1, 1, 1, 1], 4))

    def test_invalid_prediction(self):
        for codes in [[], [1], [1, 7]]:
            with self.assertRaises(ValueError):
                from_codes(codes, 2)

    def test_all_variants(self):
        self.assertEqual(matching_pattern({'pitch_patterns': [[1, 2, 2], [2, 1, 1]]},
                                          {'pitch_patterns': [[2, 1, 1]]}), [2, 1, 1])
        self.assertIsNone(matching_pattern({'pitch_patterns': [[1, 2, 1, 2]]},
                                          {'pitch_patterns': [[1, 2, 1, 1]]}))
