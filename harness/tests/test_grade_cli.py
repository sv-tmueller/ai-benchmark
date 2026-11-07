"""Unit tests for the ``grade.py`` CLI: walk/skip rules, dispatch, sidecars.

The corpus is built in a temporary directory so the tests do not depend on
the state of the real ``results/`` tree.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from harness import grade as grade_mod

SCHEMA_KEYS = {"prompt_id", "model", "mode", "pass", "detail"}

MATH_TOML = """\
id          = "math-basic"
title       = "Simple arithmetic"
file_prefix = "math-basic"

[grading]
mode     = "contains"
expected = "42"

[user]
text = "What is 17 + 25?"
"""

NOGRADE_TOML = """\
id          = "nograde"
title       = "No grading rule"
file_prefix = "nograde"

[user]
text = "Say hello."
"""

GAME_TOML = """\
id          = "game-alpha"
title       = "Alpha game"
file_prefix = "game-alpha"

[user]
text = "Build a game."
"""

SQL_EXEC_TOML = """\
id          = "sql-write"
title       = "Write a SQL query"
file_prefix = "sql-write"

[grading]
mode = "sql-exec"

[user]
text = "Write a query."
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class GradeCliTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.prompts = self.root / "prompts"
        self.results = self.root / "results"

        _write(self.prompts / "math-basic.toml", MATH_TOML)
        _write(self.prompts / "nograde.toml", NOGRADE_TOML)
        _write(self.prompts / "game-alpha.toml", GAME_TOML)

        # Gradable: contains rule via the prompt TOML.
        _write(self.results / "math-basic" / "math-basic_glm_5_3_flash.txt", "42\n")
        _write(
            self.results / "math-basic" / "math-basic_glm_5_3_flash.meta.json",
            json.dumps({"prompt_id": "math-basic", "toml": "math-basic.toml"}),
        )

        # Gradable: playability via the meta (no [grading] block anywhere).
        _write(
            self.results / "game-alpha" / "game-alpha_model_x.html",
            "<html></html>",
        )
        _write(
            self.results / "game-alpha" / "game-alpha_model_x.meta.json",
            json.dumps(
                {
                    "prompt_id": "game-alpha",
                    "playability_verification": {
                        "playability_verdict": "PLAYABLE_VERIFIED"
                    },
                }
            ),
        )

        # Skipped: prompt exists but carries no grading rule.
        _write(self.results / "nograde" / "nograde_glm_5_3_flash.md", "hi\n")
        _write(
            self.results / "nograde" / "nograde_glm_5_3_flash.meta.json",
            json.dumps({"prompt_id": "nograde"}),
        )

        # Skipped: no meta sidecar at all.
        _write(self.results / "nometa" / "nometa_glm_5_3_flash.md", "hi\n")

        # Skipped: files at the results/ root.
        _write(self.results / "gallery.html", "<html></html>")
        _write(self.results / "frontier_summary.md", "summary\n")

        # Skipped: non-result artifacts inside a result directory.
        _write(
            self.results / "math-basic" / "math-basic_glm_5_3_flash_review.html",
            "<html></html>",
        )
        _write(self.results / "game-alpha" / "rebuild_verdict.md", "verdict\n")
        _write(
            self.results / "game-alpha" / "rebuild_verdict_model_x.md", "verdict\n"
        )
        _write(self.results / "game-alpha" / "smoke_home.png", "png\n")
        _write(self.results / "game-alpha" / "smoke_home.jpg", "jpg\n")
        _write(
            self.results / "game-alpha" / "game-alpha_promo.meta.json",
            json.dumps({"promo": True}),
        )

        self.expected = {
            self.results / "math-basic" / "math-basic_glm_5_3_flash_grading.json",
            self.results / "game-alpha" / "game-alpha_model_x_grading.json",
        }

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, args, modes=None):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            try:
                code = grade_mod.main(
                    args,
                    results_dir=self.results,
                    prompts_dir=self.prompts,
                    modes=modes,
                )
            except SystemExit as exc:  # argparse rejects missing/unknown args
                code = exc.code if isinstance(exc.code, int) else 1
        return code, stdout.getvalue()

    def _sidecars(self):
        return sorted(self.results.glob("*/*_grading.json"))

    def _load(self, path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    # --- walk / skip rules ------------------------------------------------

    def test_all_writes_one_sidecar_per_gradable_result(self):
        code, _ = self._run(["--all"])

        self.assertEqual(code, 0)
        self.assertEqual(set(self._sidecars()), self.expected)

    def test_root_and_artifact_files_are_skipped(self):
        self._run(["--all"])
        names = {p.name for p in self._sidecars()}

        self.assertNotIn("gallery_grading.json", names)
        self.assertNotIn("frontier_summary_grading.json", names)
        self.assertNotIn("math-basic_glm_5_3_flash_review_grading.json", names)
        self.assertNotIn("rebuild_verdict_grading.json", names)
        self.assertNotIn("rebuild_verdict_model_x_grading.json", names)
        self.assertNotIn("smoke_home_grading.json", names)
        self.assertNotIn("game-alpha_promo_grading.json", names)

    def test_no_grading_rule_is_skipped_not_failed(self):
        self._run(["--all"])

        self.assertFalse(
            (self.results / "nograde" / "nograde_glm_5_3_flash_grading.json").exists()
        )

    def test_result_without_meta_is_skipped(self):
        self._run(["--all"])

        self.assertFalse(
            (self.results / "nometa" / "nometa_glm_5_3_flash_grading.json").exists()
        )

    def test_rerun_is_idempotent(self):
        self._run(["--all"])
        first = {p: p.read_text() for p in self._sidecars()}

        code, _ = self._run(["--all"])

        self.assertEqual(code, 0)
        self.assertEqual(set(self._sidecars()), self.expected)
        self.assertEqual({p: p.read_text() for p in self._sidecars()}, first)

    # --- sidecar contract -------------------------------------------------

    def test_sidecar_carries_exactly_the_schema_keys(self):
        self._run(["--all"])

        for path in self._sidecars():
            verdict = self._load(path)
            self.assertEqual(set(verdict), SCHEMA_KEYS)
            self.assertIsInstance(verdict["prompt_id"], str)
            self.assertIsInstance(verdict["model"], str)
            self.assertIsInstance(verdict["mode"], str)
            self.assertIsInstance(verdict["pass"], bool)
            self.assertIsInstance(verdict["detail"], str)

    def test_math_addition_sidecar_reproduces_known_pass(self):
        self._run(["--all"])

        verdict = self._load(
            self.results / "math-basic" / "math-basic_glm_5_3_flash_grading.json"
        )

        self.assertEqual(
            verdict,
            {
                "prompt_id": "math-basic",
                "model": "glm_5_3_flash",
                "mode": "contains",
                "pass": True,
                "detail": 'expected "42" found',
            },
        )

    def test_model_keeps_underscores_and_name_suffixes(self):
        _write(self.results / "game-alpha" / "game-alpha_model_x-v2.html", "<html/>")
        _write(
            self.results / "game-alpha" / "game-alpha_model_x-v2.meta.json",
            json.dumps({"prompt_id": "game-alpha", "playability": {"label": "BOOTS_ONLY"}}),
        )

        self._run(["--all"])

        verdict = self._load(
            self.results / "game-alpha" / "game-alpha_model_x-v2_grading.json"
        )
        self.assertEqual(verdict["model"], "model_x-v2")

    def test_playability_pass_follows_the_label(self):
        _write(self.results / "game-alpha" / "game-alpha_model_x-v2.html", "<html/>")
        _write(
            self.results / "game-alpha" / "game-alpha_model_x-v2.meta.json",
            json.dumps(
                {
                    "prompt_id": "game-alpha",
                    "playability": {"label": "BROKEN_AT_BOOT"},
                }
            ),
        )

        self._run(["--all"])

        playable = self._load(
            self.results / "game-alpha" / "game-alpha_model_x_grading.json"
        )
        broken = self._load(
            self.results / "game-alpha" / "game-alpha_model_x-v2_grading.json"
        )

        self.assertIs(playable["pass"], True)
        self.assertEqual(playable["mode"], "playability")
        self.assertIs(broken["pass"], False)
        self.assertEqual(broken["detail"], "playability verdict: BROKEN_AT_BOOT")

    # --- dispatch / CLI ---------------------------------------------------

    def test_single_prompt_filter_limits_the_run(self):
        code, _ = self._run(["--prompt", "math-basic"])

        self.assertEqual(code, 0)
        self.assertEqual(
            self._sidecars(),
            [self.results / "math-basic" / "math-basic_glm_5_3_flash_grading.json"],
        )

    def test_unknown_prompt_id_is_an_error(self):
        code, out = self._run(["--prompt", "does-not-exist"])

        self.assertNotEqual(code, 0)
        self.assertIn("does-not-exist", out)

    def test_at_least_one_selector_is_required(self):
        code, _ = self._run([])

        self.assertNotEqual(code, 0)

    def test_discovered_modes_include_the_shipped_modes(self):
        modes = grade_mod.discover_modes()

        self.assertIn("contains", modes)
        self.assertIn("playability", modes)
        self.assertTrue(all(callable(fn) for fn in modes.values()))
        self.assertTrue(all(not name.startswith("_") for name in modes))

    # --- D1a: hyphenated mode -> underscored module ----------------------

    def test_hyphenated_mode_dispatches_to_underscored_module(self):
        """D1a: ``sql-exec`` must dispatch to ``harness/modes/sql_exec.py``."""
        _write(self.prompts / "sql-write.toml", SQL_EXEC_TOML)
        _write(self.results / "sql-write" / "sql-write_glm_5_3_flash.md", "SELECT 1\n")
        _write(
            self.results / "sql-write" / "sql-write_glm_5_3_flash.meta.json",
            json.dumps({"prompt_id": "sql-write"}),
        )

        def sql_exec_grade(result_path, grading, prompt):
            return {
                "prompt_id": prompt["id"],
                "model": "glm_5_3_flash",
                "mode": "sql-exec",
                "pass": True,
                "detail": "dispatched to sql_exec",
            }

        # ``sql_exec`` is the underscored module name grade.py must map the
        # hyphenated TOML mode string onto during its registry lookup.
        modes = dict(grade_mod.discover_modes())
        modes["sql_exec"] = sql_exec_grade

        code, out = self._run(["--all"], modes=modes)

        self.assertEqual(code, 0, out)
        self.assertNotIn("no module for mode", out)
        verdict = self._load(
            self.results / "sql-write" / "sql-write_glm_5_3_flash_grading.json"
        )
        self.assertEqual(verdict["mode"], "sql-exec")
        self.assertIs(verdict["pass"], True)

    # --- D1a: meta with a ghost prompt_id is skipped ---------------------

    def test_playability_meta_with_ghost_prompt_id_is_skipped(self):
        """A meta verdict whose prompt_id resolves to no TOML must skip."""
        _write(
            self.results / "lava-lamp" / "lava-lamp_ghost.html",
            "<html></html>",
        )
        _write(
            self.results / "lava-lamp" / "lava-lamp_ghost.meta.json",
            json.dumps(
                {
                    "prompt_id": "ghost-prompt",
                    "playability_verification": {
                        "playability_verdict": "PLAYABLE_VERIFIED"
                    },
                }
            ),
        )

        code, out = self._run(["--all"])

        self.assertEqual(code, 0, out)
        self.assertFalse(
            (self.results / "lava-lamp" / "lava-lamp_ghost_grading.json").exists()
        )

    def test_ghost_prompt_id_is_skipped_under_prompt_filter(self):
        _write(
            self.results / "lava-lamp" / "lava-lamp_ghost.html",
            "<html></html>",
        )
        _write(
            self.results / "lava-lamp" / "lava-lamp_ghost.meta.json",
            json.dumps(
                {
                    "prompt_id": "ghost-prompt",
                    "playability_verification": {
                        "playability_verdict": "PLAYABLE_VERIFIED"
                    },
                }
            ),
        )

        code, out = self._run(["--prompt", "game-alpha"])

        self.assertEqual(code, 0, out)
        self.assertFalse(
            (self.results / "lava-lamp" / "lava-lamp_ghost_grading.json").exists()
        )

    # --- README-documented --all behaviour -------------------------------

    def test_all_writes_one_sidecar_per_defined_rule(self):
        """README: one sidecar per defined [grading] block or playability meta."""
        code, _ = self._run(["--all"])

        self.assertEqual(code, 0)
        self.assertEqual(len(self._sidecars()), 2)
        self.assertEqual({p.name for p in self._sidecars()},
                         {"math-basic_glm_5_3_flash_grading.json",
                          "game-alpha_model_x_grading.json"})


if __name__ == "__main__":
    unittest.main()
