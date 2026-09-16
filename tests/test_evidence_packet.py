import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_packet import render_model_packet, validate_packet


def demo_packet() -> dict:
    return json.loads(
        (APP_ROOT / "data" / "demo_evidence_packet_cross_modality_v1.json").read_text(encoding="utf-8")
    )


def cohort_registry() -> dict:
    return json.loads((APP_ROOT / "config" / "cohort_registry_v2.json").read_text(encoding="utf-8"))


class EvidencePacketTests(unittest.TestCase):
    def test_valid_registered_packet_renders_without_reference_standard(self) -> None:
        packet = demo_packet()
        self.assertEqual(validate_packet(packet, cohort_registry()), [])
        visible = render_model_packet(packet)
        self.assertNotIn("reference_standard", visible)
        self.assertEqual(set(visible), {"packet_id", "scope", "question", "evidence_items"})

    def test_unregistered_cohort_is_rejected(self) -> None:
        packet = demo_packet()
        packet["evidence_items"][0]["cohort_id"] = "NOT-A-COHORT"
        errors = validate_packet(packet, cohort_registry())
        self.assertIn("Evidence item 1 references unregistered cohort: NOT-A-COHORT.", errors)

    def test_evaluator_only_guard_is_required(self) -> None:
        packet = demo_packet()
        packet["reference_standard"]["evaluator_only"] = False
        errors = validate_packet(packet, cohort_registry())
        self.assertIn("reference_standard.evaluator_only must be true to prevent label leakage.", errors)
