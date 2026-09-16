import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.evidence_packet import validate_packet


class RealControlPacketTests(unittest.TestCase):
    def test_generated_real_control_packets_are_one_dependency_cluster_and_hard_negatives(self) -> None:
        registry = json.loads((APP_ROOT / "config" / "cohort_registry_v2.json").read_text(encoding="utf-8"))
        suite_dir = APP_ROOT / "data" / "real_control_packets_v1"
        manifest = json.loads((suite_dir / "manifest_v1.json").read_text(encoding="utf-8"))
        packets = [
            json.loads((suite_dir / entry["file"]).read_text(encoding="utf-8"))
            for entry in manifest["packets"]
        ]
        self.assertEqual(len(packets), 15)
        self.assertEqual(
            {packet["dependency_cluster"] for packet in packets},
            {"GSE120575_GSE91061_positive_control_panel_v1"},
        )
        self.assertTrue(all(validate_packet(packet, registry) == [] for packet in packets))
        self.assertTrue(
            all(packet["reference_standard"]["eligible_for_high_priority"] is False for packet in packets)
        )

    def test_dual_bulk_real_packets_remain_one_transport_limited_dependency_cluster(self) -> None:
        registry = json.loads((APP_ROOT / "config" / "cohort_registry_v2.json").read_text(encoding="utf-8"))
        suite_dir = APP_ROOT / "data" / "real_control_packets_v2"
        manifest = json.loads((suite_dir / "manifest_v1.json").read_text(encoding="utf-8"))
        packets = [
            json.loads((suite_dir / entry["file"]).read_text(encoding="utf-8"))
            for entry in manifest["packets"]
        ]
        self.assertEqual(len(packets), 15)
        self.assertEqual(
            {packet["dependency_cluster"] for packet in packets},
            {"GSE120575_GSE91061_GSE78220_positive_control_panel_v2"},
        )
        self.assertTrue(all(validate_packet(packet, registry) == [] for packet in packets))
        self.assertTrue(
            all(
                [item["cohort_id"] for item in packet["evidence_items"]]
                == ["GSE120575", "GSE91061", "GSE78220"]
                for packet in packets
            )
        )
        self.assertTrue(
            all(packet["reference_standard"]["eligible_for_high_priority"] is False for packet in packets)
        )
