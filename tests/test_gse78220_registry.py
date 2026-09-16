import json
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]


class GSE78220RegistryTests(unittest.TestCase):
    def test_gse78220_is_direction_eligible_but_not_same_measurement_replication(self) -> None:
        registry = json.loads((APP_ROOT / "config" / "cohort_registry_v2.json").read_text(encoding="utf-8"))
        cohort = registry["cohorts"]["GSE78220"]
        self.assertEqual(cohort["role"], "external_direction_check_only")
        self.assertTrue(cohort["baseline_ici_response_association_eligible"])
        self.assertFalse(cohort["same_measurement_replication_eligible"])
        self.assertEqual(cohort["compartment"], "tumor_bulk")
        self.assertEqual(cohort["measurement_level"], "bulk_rna")
        self.assertEqual(cohort["source_independence_group"], "gse78220_public_cohort")
