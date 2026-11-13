"""Unit tests for ``merge_results.py``: gate, ledger rewrite, orchestration.

Nothing here touches the network or the real repo state: every git and gh
call goes through the ``run`` seam, which the tests replace with a scripted
``FakeRunner``. Prompt TOMLs and PR payloads are inline fixtures.
"""

import contextlib
import io
import json
import re
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from harness import merge_results as mr

MODEL_ID = "claude-fable-5-2"
TAG = "claude_fable_5_2"

ALPHA_TOML = """\
id          = "game-alpha"
title       = "Alpha game"
file_prefix = "alpha"
save_as     = "html"

[user]
text = "Build a game."
"""

BETA_TOML = """\
id          = "app-beta"
title       = "Beta app"
file_prefix = "beta"
save_as     = "md"

[grading]
mode     = "contains"
expected = "x"

[user]
text = "Build an app."
"""

GAMMA_TOML = """\
id      = "game-gamma"
title   = "Gamma game, no file_prefix"
save_as = "html"

[user]
text = "Build a game."
"""

PARAM_TOML = """\
id          = "param-delta"
title       = "Parametrized"
file_prefix = "delta"
save_as     = "txt"

[user]
text = "Hello {x}."
"""


def prompt_entry(stem, text, fixtures=False):
    return {"stem": stem, "data": tomllib.loads(text), "fixtures": fixtures}


PROMPTS = [
    prompt_entry("game-alpha", ALPHA_TOML),
    prompt_entry("app-beta", BETA_TOML),
    prompt_entry("game-gamma", GAMMA_TOML),
    prompt_entry("param-delta", PARAM_TOML, fixtures=True),
]

MAIN_PATHS = {
    "results/alpha/alpha_other_model.html",
    "results/alpha/alpha_other_model.meta.json",
    "results/beta/beta_other_model.md",
    "results/beta/beta_other_model.meta.json",
    "results/gamma/game-gamma_other_model.html",
    "results/gamma/game-gamma_other_model.meta.json",
}

GREEN = [{"name": "validate-prompts (3.11)", "bucket": "pass"}]


def pr_files(*paths):
    return [{"path": p, "additions": 5, "deletions": 0} for p in paths]


def make_pr(prefix="alpha", number=7, ext="html", family=None, tag=TAG,
            model_id=MODEL_ID, files=None, **overrides):
    family = family or prefix
    base = "results/%s/%s_%s" % (family, prefix, tag)
    pr = {
        "number": number,
        "title": "%s (%s, one-shot): result" % (prefix, model_id),
        "headRefName": "feat/%d-%s-%s-result" % (number, prefix, tag.replace("_", "-")),
        "headRefOid": "a" * 40,
        "isDraft": False,
        "isCrossRepository": False,
        "mergeStateStatus": "CLEAN",
        "files": files if files is not None else pr_files(
            "%s.%s" % (base, ext), base + ".meta.json"),
    }
    pr.update(overrides)
    return pr


def run_gate(pr, checks=GREEN, main_paths=MAIN_PATHS, prompts=PROMPTS,
             model_id=MODEL_ID, tag=TAG):
    return mr.gate(pr, checks, main_paths, prompts, model_id, tag)


class ModelTagTests(unittest.TestCase):
    def test_plain_id(self):
        self.assertEqual(mr.normalize_model_id("claude-fable-5-2"), "claude-fable-5-2")
        self.assertEqual(mr.model_tag("claude-fable-5-2"), "claude_fable_5_2")

    def test_context_suffix_is_stripped(self):
        model_id = mr.normalize_model_id("  claude-opus-5-5[1m] ")
        self.assertEqual(model_id, "claude-opus-5-5")
        self.assertEqual(mr.model_tag(model_id), "claude_opus_5_5")

    def test_date_suffix_is_dropped_from_tag(self):
        self.assertEqual(mr.model_tag("claude-fable-5-2-20261001"), "claude_fable_5_2")

    def test_tag_is_lowercased(self):
        self.assertEqual(mr.model_tag("GLM-5.2"), "glm_5_2")

    def test_unusable_tag_is_rejected(self):
        for bad in ("", "   ", "5-2", "---", "[1m]"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    mr.model_tag(mr.normalize_model_id(bad))


class ParseTitleTests(unittest.TestCase):
    def test_result_title(self):
        self.assertEqual(
            mr.parse_title("melon-jelly (claude-fable-5-2, one-shot): result"),
            ("melon-jelly", "claude-fable-5-2"),
        )

    def test_other_titles_do_not_parse(self):
        for title in (
            "feat(results): add melon-jelly",
            "melon-jelly (claude-fable-5-2, one-shot): result extra",
            "melon-jelly (a, b, one-shot): result",
            "melon jelly (claude-fable-5-2, one-shot): result",
            "",
        ):
            with self.subTest(title=title):
                self.assertIsNone(mr.parse_title(title))


class GateTests(unittest.TestCase):
    def assertReason(self, reasons, fragment):
        self.assertTrue(
            any(fragment in r for r in reasons),
            "no reason containing %r in %r" % (fragment, reasons),
        )

    def test_clean_pass_two_files(self):
        self.assertEqual(run_gate(make_pr()), [])

    def test_clean_pass_three_files_with_grading(self):
        base = "results/beta/beta_%s" % TAG
        pr = make_pr("beta", ext="md", files=pr_files(
            base + ".md", base + ".meta.json", base + "_grading.json"))
        self.assertEqual(run_gate(pr), [])

    def test_clean_pass_prompt_without_file_prefix_uses_stem(self):
        self.assertEqual(run_gate(make_pr("game-gamma", family="gamma")), [])

    def test_grading_sidecar_without_grading_table_is_extra(self):
        base = "results/alpha/alpha_%s" % TAG
        pr = make_pr(files=pr_files(
            base + ".html", base + ".meta.json", base + "_grading.json"))
        self.assertReason(run_gate(pr), "extra file: " + base + "_grading.json")

    def test_extra_file(self):
        base = "results/alpha/alpha_%s" % TAG
        pr = make_pr(files=pr_files(
            base + ".html", base + ".meta.json", "results/alpha/notes.txt"))
        self.assertReason(run_gate(pr), "extra file: results/alpha/notes.txt")

    def test_missing_meta(self):
        base = "results/alpha/alpha_%s" % TAG
        pr = make_pr(files=pr_files(base + ".html"))
        self.assertReason(run_gate(pr), "missing: " + base + ".meta.json")

    def test_wrong_extension_is_extra_and_missing(self):
        base = "results/alpha/alpha_%s" % TAG
        pr = make_pr(files=pr_files(base + ".md", base + ".meta.json"))
        reasons = run_gate(pr)
        self.assertReason(reasons, "extra file: " + base + ".md")
        self.assertReason(reasons, "missing: " + base + ".html")

    def test_foreign_folder(self):
        pr = make_pr(family="beta")
        self.assertReason(run_gate(pr), "wrong folder")

    def test_two_folders(self):
        pr = make_pr(files=pr_files(
            "results/alpha/alpha_%s.html" % TAG,
            "results/beta/alpha_%s.meta.json" % TAG))
        self.assertReason(run_gate(pr), "wrong folder")

    def test_outside_results(self):
        pr = make_pr(files=pr_files(
            "README.md", "results/alpha/alpha_%s.meta.json" % TAG))
        self.assertReason(run_gate(pr), "wrong folder")

    def test_prefix_with_two_folders_on_main_is_ambiguous(self):
        main = MAIN_PATHS | {"results/alpha-old/alpha_older.meta.json"}
        self.assertReason(run_gate(make_pr(), main_paths=main), "wrong folder")

    def test_red_checks(self):
        checks = [{"name": "validate-prompts (3.11)", "bucket": "fail"}]
        self.assertReason(run_gate(make_pr(), checks=checks),
                          "checks red: validate-prompts (3.11)")

    def test_pending_checks(self):
        checks = [{"name": "validate-prompts (3.11)", "bucket": "pending"}]
        self.assertReason(run_gate(make_pr(), checks=checks), "checks pending")

    def test_no_checks(self):
        self.assertReason(run_gate(make_pr(), checks=[]), "no checks reported")

    def test_skipping_checks_pass(self):
        checks = GREEN + [{"name": "optional", "bucket": "skipping"}]
        self.assertEqual(run_gate(make_pr(), checks=checks), [])

    def test_file_already_on_main(self):
        main = MAIN_PATHS | {"results/alpha/alpha_%s.html" % TAG}
        self.assertReason(run_gate(make_pr(), main_paths=main), "already on main")

    def test_deletions_are_refused(self):
        files = make_pr()["files"]
        files[0]["deletions"] = 2
        self.assertReason(run_gate(make_pr(files=files)), "deletes lines")

    def test_v2_tag_is_not_the_model_tag(self):
        pr = make_pr(tag=TAG + "-v2")
        reasons = run_gate(pr)
        self.assertTrue(reasons)
        self.assertReason(reasons, "branch")

    def test_v2_files_with_matching_branch_fail_tag_cross_check(self):
        base = "results/alpha/alpha_%s-v2" % TAG
        pr = make_pr(files=pr_files(base + ".html", base + ".meta.json"))
        self.assertTrue(run_gate(pr))

    def test_branch_mismatch(self):
        pr = make_pr(headRefName="feat/7-alpha-someone-else-result")
        self.assertReason(run_gate(pr), "branch")

    def test_branch_requires_issue_number(self):
        pr = make_pr(headRefName="feat/alpha-%s-result" % TAG.replace("_", "-"))
        self.assertReason(run_gate(pr), "branch")

    def test_draft(self):
        self.assertReason(run_gate(make_pr(isDraft=True)), "draft")

    def test_fork(self):
        self.assertReason(run_gate(make_pr(isCrossRepository=True)), "fork")

    def test_unknown_prefix_has_no_prompt(self):
        pr = make_pr("zzz")
        self.assertReason(run_gate(pr), "prompt")

    def test_parametrized_prompt_is_refused(self):
        pr = make_pr("delta", ext="txt")
        self.assertReason(run_gate(pr), "fixtures")

    def test_two_prompts_with_same_prefix_is_ambiguous(self):
        prompts = PROMPTS + [prompt_entry("alpha-copy", ALPHA_TOML)]
        self.assertReason(run_gate(make_pr(), prompts=prompts), "prompt")

    def test_title_for_another_model(self):
        pr = make_pr(title="alpha (other-model, one-shot): result")
        self.assertReason(run_gate(pr), "title")

    def test_every_reason_is_collected(self):
        pr = make_pr(isDraft=True, headRefName="feat/x")
        reasons = run_gate(pr, checks=[])
        self.assertGreaterEqual(len(reasons), 3)

README = """\
# Title

Some prose with | pipes | in it.

| Prompt | Deliverable | Target path | Status |
|---|---|---|---|
| `game-alpha` | HTML | `results/alpha/alpha_claude_fable_5_2.html` | not run |
| `app-beta` | blueprint (md) | `results/beta/beta_claude_fable_5_2.md` | not run |
| `game-gamma` | HTML | `results/gamma/game-gamma_claude_fable_5_2.html` | PLAYABLE_VERIFIED |
| `game-alpha` | HTML | `results/alpha/alpha_fable_5_2.html` | not run |
| `game-alpha` | HTML | `results/alpha/alpha_claude_opus_5_5.html` | not run |
| `unknown-prompt` | HTML | `results/zzz/zzz_claude_fable_5_2.html` | not run |

## CI
"""

ALPHA_DONE = {
    "results/alpha/alpha_claude_fable_5_2.html",
    "results/alpha/alpha_claude_fable_5_2.meta.json",
}
BETA_DONE = {
    "results/beta/beta_claude_fable_5_2.md",
    "results/beta/beta_claude_fable_5_2.meta.json",
}
GAMMA_DONE = {
    "results/gamma/game-gamma_claude_fable_5_2.html",
    "results/gamma/game-gamma_claude_fable_5_2.meta.json",
}
BY_ID = mr.prompts_by_id(PROMPTS)


def rewrite(text=README, tag=TAG, main_paths=MAIN_PATHS | ALPHA_DONE | BETA_DONE | GAMMA_DONE):
    return mr.rewrite_ledger(text, tag, BY_ID, main_paths)


def status_cell(text, path):
    for line in text.splitlines():
        if "`%s`" % path in line:
            return line.split("|")[4].strip()
    raise AssertionError("no row for " + path)


class LedgerTests(unittest.TestCase):
    def test_row_updated_when_both_files_on_main(self):
        new, updated, _ = rewrite()
        self.assertEqual(status_cell(new, "results/alpha/alpha_claude_fable_5_2.html"),
                         "generated, browser check pending")
        self.assertEqual(status_cell(new, "results/beta/beta_claude_fable_5_2.md"),
                         "generated, browser check pending")
        self.assertEqual([row["pid"] for row in updated], ["game-alpha", "app-beta"])

    def test_row_untouched_when_deliverable_not_on_main(self):
        new, updated, _ = rewrite(main_paths=MAIN_PATHS | BETA_DONE)
        self.assertEqual(status_cell(new, "results/alpha/alpha_claude_fable_5_2.html"), "not run")
        self.assertEqual([row["pid"] for row in updated], ["app-beta"])

    def test_row_with_missing_sidecar_is_untouched_and_reported(self):
        paths = MAIN_PATHS | {"results/alpha/alpha_claude_fable_5_2.html"}
        new, updated, skipped = rewrite(main_paths=paths)
        self.assertEqual(new, README)
        self.assertEqual(updated, [])
        self.assertEqual(len(skipped), 1)
        self.assertIn("left as not run: sidecar missing", skipped[0])
        self.assertIn("game-alpha", skipped[0])

    def test_grading_sidecar_is_not_required(self):
        new, updated, _ = rewrite(main_paths=MAIN_PATHS | BETA_DONE)
        self.assertEqual([row["pid"] for row in updated], ["app-beta"])

    def test_row_with_a_verdict_is_never_overwritten(self):
        new, updated, _ = rewrite()
        self.assertEqual(
            status_cell(new, "results/gamma/game-gamma_claude_fable_5_2.html"),
            "PLAYABLE_VERIFIED")
        self.assertNotIn("game-gamma", [row["pid"] for row in updated])

    def test_other_models_tag_changes_nothing(self):
        paths = MAIN_PATHS | {"results/alpha/alpha_claude_opus_5_5.html",
                              "results/alpha/alpha_claude_opus_5_5.meta.json"}
        new, updated, _ = rewrite(tag="claude_opus_5_5", main_paths=paths)
        self.assertEqual([row["path"] for row in updated],
                         ["results/alpha/alpha_claude_opus_5_5.html"])
        self.assertEqual(status_cell(new, "results/alpha/alpha_claude_fable_5_2.html"), "not run")

    def test_suffix_match_is_not_enough(self):
        # `alpha_fable_5_2` ends with `_fable_5_2` but belongs to another tag.
        paths = MAIN_PATHS | {"results/alpha/alpha_fable_5_2.html",
                              "results/alpha/alpha_fable_5_2.meta.json"}
        new, updated, _ = rewrite(tag="claude_fable_5_2", main_paths=paths)
        self.assertEqual(status_cell(new, "results/alpha/alpha_fable_5_2.html"), "not run")

    def test_rewrite_is_idempotent(self):
        once, _, _ = rewrite()
        twice, updated, _ = rewrite(text=once)
        self.assertEqual(twice, once)
        self.assertEqual(updated, [])

    def test_only_status_cells_differ(self):
        new, _, _ = rewrite()
        old_lines, new_lines = README.splitlines(), new.splitlines()
        self.assertEqual(len(old_lines), len(new_lines))
        changed = 0
        for old, now in zip(old_lines, new_lines):
            if old == now:
                continue
            changed += 1
            self.assertEqual(old.rsplit("|", 2)[0], now.rsplit("|", 2)[0])
            self.assertEqual(old.rsplit("|", 2)[1].strip(), "not run")
        self.assertEqual(changed, 2)

    def test_unknown_prompt_row_is_skipped(self):
        paths = MAIN_PATHS | {"results/zzz/zzz_claude_fable_5_2.html",
                              "results/zzz/zzz_claude_fable_5_2.meta.json"}
        new, updated, _ = rewrite(main_paths=paths)
        self.assertEqual(status_cell(new, "results/zzz/zzz_claude_fable_5_2.html"), "not run")

    def test_real_readme_has_eleven_rows_for_fable(self):
        text = (mr.REPO_ROOT / "README.md").read_text(encoding="utf-8")
        prompts = mr.prompts_by_id(mr.load_prompt_files(mr.PROMPTS_DIR))
        rows = mr.ledger_rows(text, "claude_fable_5_2", prompts)
        self.assertEqual(len(rows), 11)


if __name__ == "__main__":
    unittest.main()
