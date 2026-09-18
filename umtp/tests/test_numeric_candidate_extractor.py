import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.numeric_candidate_extractor import extract_numeric_candidates  # noqa: E402


class NumericCandidateExtractorTest(unittest.TestCase):
    def test_display_and_terabytes_do_not_become_ram(self):
        candidates = extract_numeric_candidates("16.2인치 8TB")
        self.assertEqual(candidates["screen_candidates"], [16])
        self.assertEqual(candidates["ram_candidates"], [])
        self.assertEqual(candidates["ssd_candidates"], [8192])

    def test_ram_does_not_become_a_display(self):
        for token in ("16GB", "16g", "16 RAM", "램 16", "16/512"):
            with self.subTest(token=token):
                candidates = extract_numeric_candidates(token)
                self.assertEqual(candidates["screen_candidates"], [])
                self.assertEqual(candidates["ram_candidates"], [16])

    def test_high_capacity_shorthand(self):
        for token in ("128/8TB", "128/8t", "128/8테라", "128/8192"):
            with self.subTest(token=token):
                candidates = extract_numeric_candidates(f"14-inch {token}")
                self.assertEqual(candidates["screen_candidates"], [14])
                self.assertEqual(candidates["ram_candidates"], [128])
                self.assertEqual(candidates["ssd_candidates"], [8192])


if __name__ == "__main__":
    unittest.main()
