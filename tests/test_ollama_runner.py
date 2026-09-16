import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from src.ollama_runner import build_prompt, prompt_sha256


def demo_packet() -> dict:
    return json.loads(
        (APP_ROOT / "data" / "demo_evidence_packet_cross_modality_v1.json").read_text(encoding="utf-8")
    )


class OllamaRunnerTests(unittest.TestCase):
    def test_prompts_never_include_evaluator_only_reference_standard(self) -> None:
        for condition in ("free_form", "free_form_neutral", "gated_card", "schema_constrained_card", "schema_only_card"):
            prompt = build_prompt(APP_ROOT, demo_packet(), condition)
            self.assertIn("ICB-CROSS-MODALITY-001", prompt)
            self.assertNotIn("reference_standard", prompt)
            self.assertNotIn("cross_modality_direction_disagreement", prompt)

    def test_prompt_digest_is_stable(self) -> None:
        prompt = build_prompt(APP_ROOT, demo_packet(), "free_form")
        self.assertEqual(prompt_sha256(prompt), prompt_sha256(prompt))

    def test_neutral_free_form_prompt_does_not_embed_tracer_content_rules(self) -> None:
        template = (APP_ROOT / "prompts" / "free_form_neutral_v2.txt").read_text(encoding="utf-8")
        self.assertNotIn("same-measurement", template.lower())
        self.assertNotIn("causal", template.lower())
        self.assertNotIn("confidence policy", template.lower())
