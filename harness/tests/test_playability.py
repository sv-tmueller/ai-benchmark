"""Unit tests for the ``playability`` grading mode.

The mode is meta-driven: it resolves the CDP-harness verdict from the
paired ``.meta.json``. Two meta shapes exist in ``results/`` and both must
be read.
"""

import json
import tempfile
import unittest
from pathlib import Path

from harness.modes.playability import grade

SCHEMA_KEYS = {"prompt_id", "model", "mode", "pass", "detail"}


class PlayabilityModeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.prompt = {"id": "game-melon-jelly"}
        self.result = self.tmp / "melon-jelly" / "melon-jelly_glm_5_3_flash.html"
        self.result.parent.mkdir(parents=True)
        self.result.write_text("<html></html>", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _meta(self, payload):
        self.result.with_name(self.result.stem + ".meta.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def _verdict(self):
        return grade(self.result, {}, self.prompt)

    def test_new_shape_playable_verified_passes(self):
        self._meta(
            {"playability_verification": {"playability_verdict": "PLAYABLE_VERIFIED"}}
        )

        verdict = self._verdict()

        self.assertIs(verdict["pass"], True)
        self.assertEqual(verdict["detail"], "playability verdict: PLAYABLE_VERIFIED")

    def test_new_shape_broken_at_boot_fails(self):
        self._meta(
            {"playability_verification": {"playability_verdict": "BROKEN_AT_BOOT"}}
        )

        verdict = self._verdict()

        self.assertIs(verdict["pass"], False)
        self.assertEqual(verdict["detail"], "playability verdict: BROKEN_AT_BOOT")

    def test_old_shape_label_is_read(self):
        self._meta({"playability": {"label": "BOOTS_ONLY"}})

        verdict = self._verdict()

        self.assertIs(verdict["pass"], False)
        self.assertEqual(verdict["detail"], "playability verdict: BOOTS_ONLY")

    def test_old_shape_blueprint_label_fails(self):
        self._meta({"playability": {"label": "BLUEPRINT_ONLY"}})

        verdict = self._verdict()

        self.assertIs(verdict["pass"], False)
        self.assertEqual(verdict["detail"], "playability verdict: BLUEPRINT_ONLY")

    def test_new_shape_wins_when_both_shapes_present(self):
        self._meta(
            {
                "playability_verification": {"playability_verdict": "PLAYABLE_VERIFIED"},
                "playability": {"label": "BROKEN_AT_BOOT"},
            }
        )

        verdict = self._verdict()

        self.assertIs(verdict["pass"], True)
        self.assertEqual(verdict["detail"], "playability verdict: PLAYABLE_VERIFIED")

    def test_missing_meta_fails(self):
        verdict = self._verdict()

        self.assertIs(verdict["pass"], False)
        self.assertTrue(verdict["detail"])

    def test_meta_without_verdict_fails(self):
        self._meta({"prompt_id": "game-melon-jelly"})

        verdict = self._verdict()

        self.assertIs(verdict["pass"], False)
        self.assertTrue(verdict["detail"])

    def test_verdict_carries_exactly_the_schema_keys(self):
        self._meta(
            {"playability_verification": {"playability_verdict": "PLAYABLE_VERIFIED"}}
        )

        verdict = self._verdict()

        self.assertEqual(set(verdict), SCHEMA_KEYS)
        self.assertEqual(verdict["prompt_id"], "game-melon-jelly")
        self.assertEqual(verdict["model"], "glm_5_3_flash")
        self.assertEqual(verdict["mode"], "playability")


if __name__ == "__main__":
    unittest.main()
