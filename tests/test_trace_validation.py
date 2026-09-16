import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.trace_validation import extract_json_object


class TraceValidationTests(unittest.TestCase):
    def test_extracts_one_fenced_json_object(self) -> None:
        self.assertEqual(extract_json_object('```json\n{"answer": 1}\n```'), {"answer": 1})

    def test_rejects_prose_wrapped_json(self) -> None:
        with self.assertRaises(ValueError):
            extract_json_object('Here is JSON: {"answer": 1}')
