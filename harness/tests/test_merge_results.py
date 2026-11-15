"""Unit tests for ``merge_results.py``: gate, ledger rewrite, orchestration.

Nothing here touches the network or the real repo state: every git and gh
call goes through the ``run`` seam, which the tests replace with a scripted
``FakeRunner``. Prompt TOMLs and PR payloads are inline fixtures.
"""

import ast
import base64
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
import urllib.parse
from pathlib import Path

from harness import dashboard
from harness import merge_results as mr

MODEL_ID = "claude-fable-5-2"
TAG = "claude_fable_5_2"  # the model tag
RUN = TAG + "_high"  # the run tag: model tag and effort level

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

GAME_EPS_TOML = """\
id      = "game-eps"
title   = "Stem differs from id, no file_prefix"
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
    return [{"path": p, "additions": 5, "deletions": 0, "changeType": "ADDED"}
            for p in paths]


def make_pr(prefix="alpha", number=7, ext="html", family=None, tag=TAG,
            model_id=MODEL_ID, effort="high", files=None, **overrides):
    family = family or prefix
    tag = "%s_%s" % (tag, effort)
    base = "results/%s/%s_%s" % (family, prefix, tag)
    pr = {
        "number": number,
        "title": "%s (%s, %s, one-shot): result" % (prefix, model_id, effort),
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
            mr.parse_title("melon-jelly (claude-fable-5-2, xhigh, one-shot): result"),
            ("melon-jelly", "claude-fable-5-2", "xhigh"),
        )

    def test_other_titles_do_not_parse(self):
        for title in (
            "feat(results): add melon-jelly",
            "melon-jelly (claude-fable-5-2, high, one-shot): result extra",
            "melon-jelly (a, b, high, one-shot): result",
            "melon jelly (claude-fable-5-2, high, one-shot): result",
            "melon-jelly (claude-fable-5-2, one-shot): result",
            "melon-jelly (claude-fable-5-2, turbo, one-shot): result",
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
        base = "results/beta/beta_%s" % RUN
        pr = make_pr("beta", ext="md", files=pr_files(
            base + ".md", base + ".meta.json", base + "_grading.json"))
        self.assertEqual(run_gate(pr), [])

    def test_clean_pass_prompt_without_file_prefix_uses_stem(self):
        self.assertEqual(run_gate(make_pr("game-gamma", family="gamma")), [])

    def test_clean_pass_with_run_file(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(
            base + ".html", base + ".meta.json", base + ".run.json"))
        self.assertEqual(run_gate(pr), [])

    def test_clean_pass_graded_prompt_with_run_file(self):
        base = "results/beta/beta_%s" % RUN
        pr = make_pr("beta", ext="md", files=pr_files(
            base + ".md", base + ".meta.json", base + "_grading.json",
            base + ".run.json"))
        self.assertEqual(run_gate(pr), [])

    def test_run_file_of_another_effort_is_extra(self):
        base = "results/alpha/alpha_%s" % RUN
        other = "results/alpha/alpha_%s.run.json" % RUN.replace("high", "max")
        self.assertNotEqual(base + ".run.json", other)
        pr = make_pr(files=pr_files(
            base + ".html", base + ".meta.json", other))
        self.assertEqual(run_gate(pr), ["extra file: " + other])

    def test_run_file_with_another_base_name_is_extra(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(
            base + ".html", base + ".meta.json", "results/alpha/other.run.json"))
        self.assertEqual(run_gate(pr), ["extra file: results/alpha/other.run.json"])

    def test_run_file_plus_other_extra_reports_only_the_other(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(
            base + ".html", base + ".meta.json", base + ".run.json",
            "results/alpha/notes.txt"))
        self.assertEqual(run_gate(pr), ["extra file: results/alpha/notes.txt"])

    def test_run_file_without_deliverable_reports_it_missing(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(base + ".meta.json", base + ".run.json"))
        self.assertEqual(run_gate(pr), ["missing: " + base + ".html"])

    def test_run_file_alone_does_not_satisfy_the_gate(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(base + ".run.json"))
        self.assertEqual(run_gate(pr), [
            "missing: " + base + ".html", "missing: " + base + ".meta.json"])

    def test_modified_run_file_is_refused(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(
            base + ".html", base + ".meta.json", base + ".run.json"))
        pr["files"][2]["changeType"] = "MODIFIED"
        self.assertReason(run_gate(pr), "not a new file (MODIFIED): " + base + ".run.json")

    def test_run_file_already_on_main_is_refused(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(
            base + ".html", base + ".meta.json", base + ".run.json"))
        main = MAIN_PATHS | {base + ".run.json"}
        self.assertReason(run_gate(pr, main_paths=main), "already on main: " + base + ".run.json")

    def test_grading_sidecar_without_grading_table_is_extra(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(
            base + ".html", base + ".meta.json", base + "_grading.json"))
        self.assertReason(run_gate(pr), "extra file: " + base + "_grading.json")

    def test_extra_file(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(
            base + ".html", base + ".meta.json", "results/alpha/notes.txt"))
        self.assertReason(run_gate(pr), "extra file: results/alpha/notes.txt")

    def test_missing_meta(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(base + ".html"))
        self.assertReason(run_gate(pr), "missing: " + base + ".meta.json")

    def test_wrong_extension_is_extra_and_missing(self):
        base = "results/alpha/alpha_%s" % RUN
        pr = make_pr(files=pr_files(base + ".md", base + ".meta.json"))
        reasons = run_gate(pr)
        self.assertReason(reasons, "extra file: " + base + ".md")
        self.assertReason(reasons, "missing: " + base + ".html")

    def test_foreign_folder(self):
        pr = make_pr(family="beta")
        self.assertReason(run_gate(pr), "wrong folder")

    def test_two_folders(self):
        pr = make_pr(files=pr_files(
            "results/alpha/alpha_%s.html" % RUN,
            "results/beta/alpha_%s.meta.json" % RUN))
        self.assertReason(run_gate(pr), "wrong folder")

    def test_outside_results(self):
        pr = make_pr(files=pr_files(
            "README.md", "results/alpha/alpha_%s.meta.json" % RUN))
        self.assertReason(run_gate(pr), "wrong folder")

    def test_prefix_with_two_folders_on_main_is_ambiguous(self):
        main = MAIN_PATHS | {"results/alpha-old/alpha_older.meta.json"}
        self.assertReason(run_gate(make_pr(), main_paths=main), "wrong folder")

    def test_first_result_of_a_prompt_uses_the_prefix_as_folder(self):
        self.assertEqual(run_gate(make_pr(), main_paths=frozenset()), [])

    def test_first_result_of_a_prompt_in_another_folder_is_rejected(self):
        pr = make_pr(family="beta")
        self.assertReason(run_gate(pr, main_paths=frozenset()), "wrong folder")

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
        main = MAIN_PATHS | {"results/alpha/alpha_%s.html" % RUN}
        self.assertReason(run_gate(make_pr(), main_paths=main), "already on main")

    def test_deletions_are_refused(self):
        files = make_pr()["files"]
        files[0]["deletions"] = 2
        self.assertReason(run_gate(make_pr(files=files)), "deletes lines")

    def test_renamed_file_is_refused(self):
        # gh lists a rename as one entry: new path, deletions 0, RENAMED.
        files = make_pr()["files"]
        files[0].update(additions=0, changeType="RENAMED")
        self.assertReason(run_gate(make_pr(files=files)), "not a new file")

    def test_modified_file_is_refused(self):
        files = make_pr()["files"]
        files[0]["changeType"] = "MODIFIED"
        self.assertReason(run_gate(make_pr(files=files)), "not a new file")

    def test_v2_tag_is_not_the_model_tag(self):
        pr = make_pr(tag=TAG + "-v2")
        reasons = run_gate(pr)
        self.assertTrue(reasons)
        self.assertReason(reasons, "branch")

    def test_v2_files_with_matching_branch_are_extra_and_missing(self):
        base = "results/alpha/alpha_%s-v2" % RUN
        pr = make_pr(files=pr_files(base + ".html", base + ".meta.json"))
        want = "results/alpha/alpha_%s" % RUN
        self.assertEqual(run_gate(pr), [
            "extra file: " + base + ".html",
            "extra file: " + base + ".meta.json",
            "missing: " + want + ".html",
            "missing: " + want + ".meta.json",
        ])

    def test_derive_model_disagreement_is_its_own_reason(self):
        # No file_prefix, an "_" in the stem, and an id that differs from the
        # stem: derive_model cannot recover the prefix, so only (g) objects.
        eps = prompt_entry("game_eps", GAME_EPS_TOML)
        pr = make_pr("game_eps", family="eps")
        main = MAIN_PATHS | {"results/eps/game_eps_other_model.meta.json"}
        self.assertEqual(
            run_gate(pr, main_paths=main, prompts=PROMPTS + [eps]),
            ["derive_model disagrees with tag %s for results/eps/game_eps_%s.html"
             % (RUN, RUN)],
        )

    def test_files_at_another_effort_than_the_title_are_extra_and_missing(self):
        base = "results/alpha/alpha_%s_max" % TAG
        pr = make_pr(files=pr_files(base + ".html", base + ".meta.json"))
        want = "results/alpha/alpha_%s" % RUN
        self.assertEqual(run_gate(pr), [
            "extra file: " + base + ".html",
            "extra file: " + base + ".meta.json",
            "missing: " + want + ".html",
            "missing: " + want + ".meta.json",
        ])

    def test_branch_at_another_effort_than_the_title_is_refused(self):
        pr = make_pr(headRefName="feat/7-alpha-%s-max-result" % TAG.replace("_", "-"))
        self.assertReason(run_gate(pr), "branch")

    def test_every_effort_level_passes_with_its_own_names(self):
        for effort in mr.EFFORT_LEVELS:
            with self.subTest(effort=effort):
                self.assertEqual(run_gate(make_pr(effort=effort)), [])

    def test_the_same_result_at_another_effort_on_main_does_not_block(self):
        main = MAIN_PATHS | {"results/alpha/alpha_%s_max.html" % TAG,
                             "results/alpha/alpha_%s_max.meta.json" % TAG}
        self.assertEqual(run_gate(make_pr(), main_paths=main), [])

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
        pr = make_pr(title="alpha (other-model, high, one-shot): result")
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
| `game-alpha` | HTML | `results/alpha/alpha_claude_fable_5_2_<effort>.html` | not run |
| `app-beta` | blueprint (md) | `results/beta/beta_claude_fable_5_2_<effort>.md` | not run |
| `game-gamma` | HTML | `results/gamma/game-gamma_claude_fable_5_2_<effort>.html` | PLAYABLE_VERIFIED |
| `game-alpha` | HTML | `results/alpha/alpha_fable_5_2_<effort>.html` | not run |
| `game-alpha` | HTML | `results/alpha/alpha_claude_opus_5_5_<effort>.html` | not run |
| `unknown-prompt` | HTML | `results/zzz/zzz_claude_fable_5_2_<effort>.html` | not run |

## CI
"""

ALPHA_DONE = {
    "results/alpha/alpha_claude_fable_5_2_high.html",
    "results/alpha/alpha_claude_fable_5_2_high.meta.json",
}
BETA_DONE = {
    "results/beta/beta_claude_fable_5_2_high.md",
    "results/beta/beta_claude_fable_5_2_high.meta.json",
}
GAMMA_DONE = {
    "results/gamma/game-gamma_claude_fable_5_2_high.html",
    "results/gamma/game-gamma_claude_fable_5_2_high.meta.json",
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
        self.assertEqual(status_cell(new, "results/alpha/alpha_claude_fable_5_2_<effort>.html"),
                         "generated (high), review pending")
        self.assertEqual(status_cell(new, "results/beta/beta_claude_fable_5_2_<effort>.md"),
                         "generated (high), review pending")
        self.assertEqual([row["pid"] for row in updated], ["game-alpha", "app-beta"])

    def test_row_untouched_when_deliverable_not_on_main(self):
        new, updated, _ = rewrite(main_paths=MAIN_PATHS | BETA_DONE)
        self.assertEqual(status_cell(new, "results/alpha/alpha_claude_fable_5_2_<effort>.html"), "not run")
        self.assertEqual([row["pid"] for row in updated], ["app-beta"])

    def test_row_with_missing_sidecar_is_untouched_and_reported(self):
        paths = MAIN_PATHS | {"results/alpha/alpha_claude_fable_5_2_high.html"}
        new, updated, skipped = rewrite(main_paths=paths)
        self.assertEqual(new, README)
        self.assertEqual(updated, [])
        self.assertEqual(len(skipped), 1)
        self.assertIn("high not listed: sidecar missing", skipped[0])
        self.assertIn("game-alpha", skipped[0])

    def test_grading_sidecar_is_not_required(self):
        new, updated, _ = rewrite(main_paths=MAIN_PATHS | BETA_DONE)
        self.assertEqual([row["pid"] for row in updated], ["app-beta"])

    def test_row_with_a_verdict_is_never_overwritten(self):
        new, updated, _ = rewrite()
        self.assertEqual(
            status_cell(new, "results/gamma/game-gamma_claude_fable_5_2_<effort>.html"),
            "PLAYABLE_VERIFIED")
        self.assertNotIn("game-gamma", [row["pid"] for row in updated])

    def test_other_models_tag_changes_nothing(self):
        paths = MAIN_PATHS | {"results/alpha/alpha_claude_opus_5_5_high.html",
                              "results/alpha/alpha_claude_opus_5_5_high.meta.json"}
        new, updated, _ = rewrite(tag="claude_opus_5_5", main_paths=paths)
        self.assertEqual([row["path"] for row in updated],
                         ["results/alpha/alpha_claude_opus_5_5_<effort>.html"])
        self.assertEqual(status_cell(new, "results/alpha/alpha_claude_fable_5_2_<effort>.html"), "not run")

    def test_suffix_match_is_not_enough(self):
        # `alpha_fable_5_2` ends with `_fable_5_2` but belongs to another tag.
        paths = MAIN_PATHS | {"results/alpha/alpha_fable_5_2_high.html",
                              "results/alpha/alpha_fable_5_2_high.meta.json"}
        new, updated, _ = rewrite(tag="claude_fable_5_2", main_paths=paths)
        self.assertEqual(status_cell(new, "results/alpha/alpha_fable_5_2_<effort>.html"), "not run")

    def test_status_lists_every_effort_on_main_in_level_order(self):
        more = {"results/alpha/alpha_claude_fable_5_2_max.html",
                "results/alpha/alpha_claude_fable_5_2_max.meta.json",
                "results/alpha/alpha_claude_fable_5_2_low.html",
                "results/alpha/alpha_claude_fable_5_2_low.meta.json"}
        new, updated, _ = rewrite(main_paths=MAIN_PATHS | ALPHA_DONE | more)
        self.assertEqual(status_cell(new, "results/alpha/alpha_claude_fable_5_2_<effort>.html"),
                         "generated (low, high, max), review pending")
        self.assertEqual(updated, [{"pid": "game-alpha",
                                    "path": "results/alpha/alpha_claude_fable_5_2_<effort>.html",
                                    "efforts": ["low", "high", "max"]}])

    def test_a_later_effort_is_added_to_a_generated_row(self):
        once, _, _ = rewrite(main_paths=MAIN_PATHS | ALPHA_DONE)
        more = {"results/alpha/alpha_claude_fable_5_2_xhigh.html",
                "results/alpha/alpha_claude_fable_5_2_xhigh.meta.json"}
        twice, updated, _ = rewrite(text=once, main_paths=MAIN_PATHS | ALPHA_DONE | more)
        self.assertEqual(status_cell(twice, "results/alpha/alpha_claude_fable_5_2_<effort>.html"),
                         "generated (high, xhigh), review pending")
        self.assertEqual([row["efforts"] for row in updated], [["high", "xhigh"]])

    def test_a_row_without_the_effort_placeholder_is_not_a_ledger_row(self):
        text = README.replace("alpha_claude_fable_5_2_<effort>.html", "alpha_claude_fable_5_2.html")
        new, updated, _ = rewrite(text=text)
        self.assertEqual(status_cell(new, "results/alpha/alpha_claude_fable_5_2.html"), "not run")
        self.assertEqual([row["pid"] for row in updated], ["app-beta"])

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
        paths = MAIN_PATHS | {"results/zzz/zzz_claude_fable_5_2_high.html",
                              "results/zzz/zzz_claude_fable_5_2_high.meta.json"}
        new, updated, _ = rewrite(main_paths=paths)
        self.assertEqual(status_cell(new, "results/zzz/zzz_claude_fable_5_2_<effort>.html"), "not run")

    def test_real_readme_has_fourteen_rows_for_fable(self):
        text = (mr.REPO_ROOT / "README.md").read_text(encoding="utf-8")
        prompts = mr.prompts_by_id(mr.load_prompt_files(mr.PROMPTS_DIR))
        rows = mr.ledger_rows(text, "claude_fable_5_2", prompts)
        self.assertEqual(len(rows), 14)


# --- orchestration ----------------------------------------------------------

LIST_ARGV = ("gh", "pr", "list", "--state", "open", "--base", "main", "--limit", "200",
             "--json", "number,title,headRefName,isDraft,isCrossRepository")
VIEW_FIELDS = ("number,title,headRefName,headRefOid,isDraft,isCrossRepository,"
               "files,mergeStateStatus")
WRITE_PREFIXES = (
    ("gh", "pr", "merge"),
    ("gh", "pr", "update-branch"),
    ("gh", "pr", "create"),
    ("gh", "api"),
)
FETCH = ("git", "fetch", "origin", "main")
LS_TREE = ("git", "ls-tree", "-r", "--name-only", "origin/main", "--", "results")
MAIN_SHA = "c" * 40
MAIN_TREE = "7" * 40  # the tree of MAIN_SHA
README_BLOB = "d" * 40
D = "e" * 40  # head of the docs PR; also the commit the fake's git/commits call creates
NEW_TREE = "4" * 40
NEW_COMMIT = D
PIN = MAIN_SHA + ":"  # the pinned reads: every read after the resolve names the sha


def ok(stdout=""):
    return (0, stdout, "")


def okb(stdout=b""):
    return (0, stdout, b"")


class FakeRunner:
    """Scripted ``run`` seam: longest argv-prefix match (latest rule wins ties).

    A response is ``(returncode, stdout, stderr)`` or a function of
    ``(argv, input)`` returning one. A call with ``binary=True`` must get bytes
    and any other call text, as ``default_run`` gives them.
    """

    def __init__(self):
        self.rules = []
        self.calls = []
        self.binary_argvs = []

    def on(self, *prefix, responses):
        self.rules.append((prefix, list(responses)))

    def __call__(self, argv, input=None, binary=False):
        argv = tuple(argv)
        self.calls.append((argv, input))
        if binary:
            self.binary_argvs.append(argv)
        best = None
        for prefix, queue in self.rules:
            if argv[:len(prefix)] == prefix and (best is None or len(prefix) >= len(best[0])):
                best = (prefix, queue)
        if best is None:
            raise AssertionError("unscripted call: %r" % (argv,))
        queue = best[1]
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        rc, stdout, stderr = item(argv, input) if callable(item) else item
        if not isinstance(stdout, bytes if binary else str):
            raise AssertionError("wrong stdout type for binary=%r: %r" % (binary, argv))
        return subprocess.CompletedProcess(argv, rc, stdout, stderr)

    def argvs(self):
        return [argv for argv, _ in self.calls]

    def writes(self):
        return [a for a in self.argvs() if any(a[:len(p)] == p for p in WRITE_PREFIXES)]

    def find(self, *prefix):
        return [(a, i) for a, i in self.calls if a[:len(prefix)] == prefix]


def tree(paths):
    return ok("\n".join(sorted(paths)) + "\n")


def listing(prs, extra=()):
    items = [{k: pr[k] for k in ("number", "title", "headRefName", "isDraft",
                                 "isCrossRepository")} for pr in prs]
    return ok(json.dumps(items + list(extra)))


def blob_sha(data):
    """Git blob id of ``data``; computed here so tests do not lean on the code under test."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def result_entries(paths):
    """``[(path bytes, content bytes)]`` for result ``paths``: a small sidecar or a marker."""
    entries = []
    for path in sorted(paths):
        if path.endswith(".meta.json"):
            folder, name = path.split("/")[1:]
            content = json.dumps({"prompt_id": "pid-" + folder,
                                  "title": "Title of " + name}).encode("utf-8")
        else:
            content = ("DELIVERABLE " + path).encode("utf-8")
        entries.append((path.encode("utf-8"), content))
    return entries


def expected_page(paths):
    """The dashboard bytes for result ``paths``, built through the working-tree reader.

    It reads a temporary folder, not the git tree, so the tests do not lean on
    the git reader they check.
    """
    with tempfile.TemporaryDirectory() as tmp:
        for path, content in result_entries(paths):
            target = Path(tmp, path.decode("utf-8"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        rows, _ = dashboard.collect_rows(tmp)
    return dashboard.render(rows).encode("utf-8")


def ls_tree_z(entries):
    """``git ls-tree -r -z`` output for ``(path, content)`` entries, all regular files."""
    return b"".join(b"100644 blob %s\t%s\0" % (blob_sha(content).encode("ascii"), path)
                    for path, content in sorted(entries))


def cat_file_reply(entries):
    """A scripted ``git cat-file --batch``: answers the oids it is given, from ``entries``."""
    blobs = {blob_sha(content): content for _, content in entries}

    def reply(argv, input):
        out = b""
        for oid in input.decode("ascii").split("\n")[:-1]:
            if oid in blobs:
                out += b"%s blob %d\n%s\n" % (oid.encode("ascii"), len(blobs[oid]), blobs[oid])
            else:
                out += b"%s missing\n" % oid.encode("ascii")
        return okb(out)

    return reply


def blob_reply(argv, input):
    """``POST git/blobs``: the id GitHub would answer for the posted content."""
    body = json.loads(input)
    assert body["encoding"] == "base64", body
    return ok(json.dumps({"sha": blob_sha(base64.b64decode(body["content"]))}))


GIT_DATA = "repos/{owner}/{repo}/git/"


def post_argv(endpoint):
    return ("gh", "api", "--method", "POST", "repos/{owner}/{repo}/" + endpoint, "--input", "-")


NO_DASHBOARD = (128, "", "fatal: path 'dashboard.html' does not exist in '%s'\n" % MAIN_SHA)


def build_fake(prs=(), main_before=MAIN_PATHS, main_after=None, readme=README,
               views=None, checks=None, extra_list=(), merge=None, strict_api=False,
               dashboard_on_main="current", results_at_sha=None):
    """Script a world: ``prs`` are open; ``views``/``checks``/``merge`` override per PR.

    ``strict_api`` scripts the status endpoint by full path instead of the
    catch-all ``gh api --method POST`` rule, so an unscripted endpoint (a
    status post to the wrong sha, say) raises, and answers the README blob
    with the fixture's real blob id.

    The results at ``MAIN_SHA`` are ``main_after`` (``results_at_sha`` to
    override). ``dashboard_on_main`` is the ``dashboard.html`` committed there:
    ``"current"`` is the page of those results, ``"before"`` the page of
    ``main_before`` (stale once results merged), ``"stale"`` some other page,
    ``None`` no such file, or a ready ``(rc, stdout, stderr)`` reply.
    """
    fake = FakeRunner()
    views, checks, merge = views or {}, checks or {}, merge or {}
    fake.on("gh", "auth", "status", responses=[ok()])
    fake.on(*FETCH, responses=[ok()])
    fake.on(*LIST_ARGV, responses=[listing(prs, extra_list)])
    after = main_before if main_after is None else main_after
    fake.on(*LS_TREE, responses=[tree(main_before), tree(after)])
    # Everything the ledger reads is read at the one resolved commit.
    fake.on("git", "rev-parse", "origin/main", responses=[ok(MAIN_SHA + "\n")])
    fake.on("git", "rev-parse", MAIN_SHA + "^{tree}", responses=[ok(MAIN_TREE + "\n")])
    fake.on("git", "show", PIN + "README.md", responses=[ok(readme)])
    blob = blob_sha(readme.encode("utf-8")) if strict_api else README_BLOB
    fake.on("git", "rev-parse", PIN + "README.md", responses=[ok(blob + "\n")])
    at_sha = after if results_at_sha is None else results_at_sha
    entries = result_entries(at_sha)
    fake.on("git", "ls-tree", "-r", "-z", MAIN_SHA, "--", "results",
            responses=[okb(ls_tree_z(entries))])
    fake.on("git", "cat-file", "--batch", responses=[cat_file_reply(entries)])
    if dashboard_on_main is None:
        reply = NO_DASHBOARD
    elif isinstance(dashboard_on_main, tuple):
        reply = dashboard_on_main
    else:
        page = {"current": lambda: expected_page(at_sha),
                "before": lambda: expected_page(main_before),
                "stale": lambda: b"<html>an old page</html>\n"}[dashboard_on_main]()
        reply = ok(blob_sha(page) + "\n")
    fake.on("git", "rev-parse", PIN + "dashboard.html", responses=[reply])
    for pr in prs:
        n = str(pr["number"])
        fake.on("gh", "pr", "view", n, "--json", VIEW_FIELDS,
                responses=views.get(pr["number"], [ok(json.dumps(pr))]))
        fake.on("gh", "pr", "checks", n, "--json", "name,bucket",
                responses=checks.get(pr["number"], [ok(json.dumps(GREEN))]))
        fake.on("gh", "pr", "merge", n, responses=merge.get(pr["number"], [ok()]))
        fake.on("gh", "pr", "update-branch", n, responses=[ok()])
    fake.on(*post_argv("git/blobs"), responses=[blob_reply])
    fake.on(*post_argv("git/trees"), responses=[ok(json.dumps({"sha": NEW_TREE}))])
    fake.on(*post_argv("git/commits"), responses=[ok(json.dumps({"sha": NEW_COMMIT}))])
    fake.on(*post_argv("git/refs"), responses=[ok("{}")])
    if not strict_api:
        fake.on("gh", "api", "--method", "POST", responses=[ok("{}")])
    fake.on("gh", "pr", "create", responses=[ok("https://github.com/o/r/pull/99\n")])
    return fake


STATUS_ENDPOINT = "repos/{owner}/{repo}/statuses/"
CONTEXTS = ("orchestrai/test", "orchestrai/review")


def status_fields(argv):
    """Return ``{sha, state, context, description}`` of a status post argv, else ``None``."""
    if argv[:4] != ("gh", "api", "--method", "POST") or STATUS_ENDPOINT not in argv[4]:
        return None
    fields = {"sha": argv[4].rsplit("/", 1)[1]}
    for flag, pair in zip(argv[5::2], argv[6::2]):
        assert flag == "-f", argv
        key, _, value = pair.partition("=")
        fields[key] = value
    return fields


REPO_API = "repos/{owner}/{repo}/"
SHA40 = r"[0-9a-f]{40}"


def api_call_problem(argv):
    """Return why a ``gh api`` argv is not one the command makes, else ``None``.

    The command makes these: the blob, tree, commit and ref POSTs that build
    the docs commit (each ``--input -``, exactly the endpoint, nothing else),
    a status POST on a full sha, and the bare commit read (a read: any extra
    field would make ``gh`` send a POST). There is no PUT: the contents
    endpoint is no longer used. Other argvs are not this check's concern.
    """
    if argv[:2] != ("gh", "api"):
        return None
    if len(argv) == 3 and re.fullmatch(REPO_API + "commits/" + SHA40, argv[2]):
        return None
    if argv[2:4] == ("--method", "POST") and len(argv) > 4:
        endpoint = argv[4]
        if endpoint in (REPO_API + "git/" + name for name in ("blobs", "trees", "commits", "refs")):
            if argv[5:] == ("--input", "-"):
                return None
        elif re.fullmatch(REPO_API + "statuses/" + SHA40, endpoint):
            return None
    return "gh api call outside the allowlist: %r" % (argv,)


def status_posts(fake):
    """Return ``[(sha, context, description)]`` for every status post the fake saw."""
    return [(f["sha"], f["context"], f["description"])
            for f in map(status_fields, fake.argvs()) if f]


def script_status(fake, sha, test=None, review=None):
    """Allow status posts on ``sha`` only, by full path and context."""
    for context, responses in zip(CONTEXTS, (test, review)):
        fake.on("gh", "api", "--method", "POST", STATUS_ENDPOINT + sha,
                "-f", "state=success", "-f", "context=" + context,
                responses=responses or [ok("{}")])


def run_main(fake, *args, model=MODEL_ID, out=None):
    sleeps = []
    out = io.StringIO() if out is None else out
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in (("game-alpha.toml", ALPHA_TOML), ("app-beta.toml", BETA_TOML)):
            Path(tmp, name).write_text(text, encoding="utf-8")
        code = mr.main(["--model=" + model, *args], run=fake, sleep=sleeps.append,
                       prompts_dir=tmp, out=out)
    return code, out.getvalue(), sleeps


class OrchestrationBase(unittest.TestCase):
    fake = None
    vouched = frozenset()  # shas that passed the gate; a status goes nowhere else

    def tearDown(self):
        if self.fake is not None:
            for argv in self.fake.argvs():
                self.assertNotIn("--admin", argv)
                self.assertNotIn("--auto", argv)
                self.assertNotIn("--delete-branch", argv)
                self.assertIsNone(api_call_problem(argv))
                fields = status_fields(argv)
                if fields:
                    self.assertIn(fields["sha"], self.vouched, argv)
                    self.assertIn(fields["context"], CONTEXTS)
                    self.assertEqual(fields["state"], "success")
                    self.assertTrue(fields["description"].startswith(mr.STATUS_MARKER))
                    self.assertLessEqual(len(fields["description"]), 140)


class ApiCallProblemTests(unittest.TestCase):
    SHA = "c" * 40
    REPO = "repos/{owner}/{repo}/"

    def test_endpoints_the_command_uses_are_allowed(self):
        for argv in (
            ("gh", "api", "--method", "POST", self.REPO + "git/blobs", "--input", "-"),
            ("gh", "api", "--method", "POST", self.REPO + "git/trees", "--input", "-"),
            ("gh", "api", "--method", "POST", self.REPO + "git/commits", "--input", "-"),
            ("gh", "api", "--method", "POST", self.REPO + "git/refs", "--input", "-"),
            ("gh", "api", "--method", "POST", self.REPO + "statuses/" + self.SHA,
             "-f", "state=success", "-f", "context=orchestrai/test"),
            ("gh", "api", self.REPO + "commits/" + self.SHA),
        ):
            with self.subTest(argv=argv):
                self.assertIsNone(api_call_problem(argv))

    def test_any_other_gh_api_call_is_flagged(self):
        for argv in (
            ("gh", "api", "--method", "PUT", self.REPO + "contents/README.md", "--input", "-"),
            ("gh", "api", "--method", "PUT", self.REPO + "contents/dashboard.html"),
            ("gh", "api", "--method", "POST", self.REPO + "git/blobs"),
            ("gh", "api", "--method", "POST", self.REPO + "git/trees", "--input", "x"),
            ("gh", "api", "--method", "POST", self.REPO + "git/tags", "--input", "-"),
            ("gh", "api", "--method", "PATCH", self.REPO + "git/refs/heads/main", "--input", "-"),
            ("gh", "api", "--method", "PUT", self.REPO + "pulls/7/merge"),
            ("gh", "api", "--method", "POST", self.REPO + "issues/7/comments"),
            ("gh", "api", "--method", "POST", self.REPO + "git/refs/heads/main"),
            ("gh", "api", "--method", "POST", self.REPO + "statuses/abc"),
            ("gh", "api", "--method", "PUT", self.REPO + "branches/main/protection"),
            ("gh", "api", self.REPO + "commits/" + self.SHA, "-f", "x=y"),
            ("gh", "api", "-X", "POST", self.REPO + "git/refs"),
            ("gh", "api", "--method", "PATCH", self.REPO + "git/refs"),
            ("gh", "api"),
        ):
            with self.subTest(argv=argv):
                self.assertIsNotNone(api_call_problem(argv))

    def test_calls_that_are_not_gh_api_are_not_its_concern(self):
        self.assertIsNone(api_call_problem(("gh", "pr", "merge", "7")))
        self.assertIsNone(api_call_problem(("git", "fetch", "origin")))


class ApiAllowlistWiringTests(OrchestrationBase):
    def test_teardown_rejects_a_write_to_an_unlisted_endpoint(self):
        # The default fake's catch-all rules accept this call; only tearDown objects.
        self.fake = build_fake()
        self.fake.on("gh", "api", "--method", "PUT", responses=[ok("{}")])
        self.fake(("gh", "api", "--method", "PUT", "repos/{owner}/{repo}/pulls/7/merge"))
        with self.assertRaises(AssertionError):
            self.tearDown()
        self.fake = None  # the real tearDown, which runs next, now passes


ALPHA_FILES = ["results/alpha/alpha_%s.html" % RUN, "results/alpha/alpha_%s.meta.json" % RUN]
BETA_FILES = ["results/beta/beta_%s.md" % RUN, "results/beta/beta_%s.meta.json" % RUN]


class NoOpTests(OrchestrationBase):
    def test_no_candidates_and_ledger_current(self):
        self.fake = build_fake()
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0)
        self.assertIn("nothing to merge; ledger up to date", out)
        self.assertEqual(self.fake.writes(), [])
        self.assertEqual(
            set(self.fake.argvs()),
            {("gh", "auth", "status"), FETCH, LIST_ARGV, LS_TREE,
             ("git", "rev-parse", "origin/main"),
             ("git", "rev-parse", MAIN_SHA + "^{tree}"),
             ("git", "show", PIN + "README.md"),
             ("git", "rev-parse", PIN + "README.md"),
             ("git", "rev-parse", PIN + "dashboard.html"),
             ("git", "ls-tree", "-r", "-z", MAIN_SHA, "--", "results"),
             ("git", "cat-file", "--batch")})
        self.assertIn("dashboard.html up to date", out)

    def test_pr_for_another_model_is_never_touched(self):
        other = make_pr(number=5, model_id="other-model", tag="other_model")
        self.fake = build_fake(prs=[other])
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.find("gh", "pr", "view"), [])
        self.assertEqual(self.fake.find("gh", "pr", "checks"), [])

    def test_non_result_pr_is_ignored(self):
        chore = make_pr(number=5, title="chore: bump things")
        self.fake = build_fake(prs=[chore])
        code, _, _ = run_main(self.fake)
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.find("gh", "pr", "view"), [])

    def test_bad_model_id_exits_2_without_calls(self):
        self.fake = build_fake()
        code, out, _ = run_main(self.fake, model="---")
        self.assertEqual(code, 2)
        self.assertEqual(self.fake.calls, [])

    def test_auth_failure_exits_2(self):
        self.fake = build_fake()
        self.fake.rules[0] = (("gh", "auth", "status"), [(1, "", "not logged in")])
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 2)
        self.assertIn("not logged in", out)
        self.assertEqual(self.fake.argvs(), [("gh", "auth", "status")])

    def test_fetch_failure_exits_2(self):
        self.fake = build_fake()
        self.fake.rules[1] = (FETCH, [(128, "", "network down")])
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 2)
        self.assertEqual(self.fake.writes(), [])


class MergeTests(OrchestrationBase):
    def test_gated_pr_is_squash_merged_then_docs_pr_opened(self):
        pr = make_pr(number=7)
        # The dashboard committed on main predates the merge: it is stale now.
        self.fake = build_fake(prs=[pr], main_after=MAIN_PATHS | set(ALPHA_FILES),
                               dashboard_on_main="before")
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0, out)
        merge_call = self.fake.find("gh", "pr", "merge")
        self.assertEqual(len(merge_call), 1)
        self.assertEqual(merge_call[0][0], (
            "gh", "pr", "merge", "7", "--squash", "--match-head-commit", "a" * 40,
            "--subject", "feat(results): add alpha %s high one-shot result (#7)" % MODEL_ID))
        branch = "docs/ledger-claude-fable-5-2-" + MAIN_SHA[:7]
        posts = [(argv[4], json.loads(body)) for argv, body in self.fake.calls
                 if argv[:4] == ("gh", "api", "--method", "POST")]
        self.assertEqual([endpoint.split("/")[-1] for endpoint, _ in posts],
                         ["blobs", "blobs", "trees", "commits", "refs"])
        contents = [base64.b64decode(body["content"]) for _, body in posts[:2]]
        new_readme = contents[0].decode("utf-8")
        self.assertEqual(
            status_cell(new_readme, "results/alpha/alpha_claude_fable_5_2_<effort>.html"),
            "generated (high), review pending")
        self.assertEqual(
            status_cell(new_readme, "results/beta/beta_claude_fable_5_2_<effort>.md"), "not run")
        self.assertEqual(contents[1], expected_page(MAIN_PATHS | set(ALPHA_FILES)))
        self.assertEqual(posts[4][1], {"ref": "refs/heads/" + branch, "sha": NEW_COMMIT})
        create = self.fake.find("gh", "pr", "create")[0][0]
        self.assertEqual(create[create.index("--head") + 1], branch)
        self.assertEqual(create[create.index("--base") + 1], "main")
        self.assertEqual(create[create.index("--title") + 1],
                         "docs(readme): mark 1 claude-fable-5-2 ledger rows generated, "
                         "regenerate dashboard")
        self.assertIn("#7", create[create.index("--body") + 1])
        self.assertIn("https://github.com/o/r/pull/99", out)

    def test_ledger_reads_main_again_after_merging(self):
        self.fake = build_fake(prs=[make_pr(number=7)],
                               main_after=MAIN_PATHS | set(ALPHA_FILES))
        run_main(self.fake)
        argvs = self.fake.argvs()
        merge_at = argvs.index(self.fake.find("gh", "pr", "merge")[0][0])
        self.assertIn(FETCH, argvs[merge_at:])
        self.assertIn(LS_TREE, argvs[merge_at:])

    def test_gate_failure_leaves_pr_open_with_reasons(self):
        pr = make_pr(number=7, isDraft=True)
        self.fake = build_fake(prs=[pr])
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: fails gate:", out)
        self.assertIn("draft", out)
        self.assertEqual(self.fake.writes(), [])

    def test_refused_merge_is_reported_and_later_prs_still_processed(self):
        first = make_pr(number=7)
        second = make_pr("beta", number=8, ext="md")
        blocked = (1, "", "X Pull request is not mergeable: the base branch policy "
                          "prohibits the merge.\nUse --admin to bypass.\n")
        views = {7: [ok(json.dumps(dict(first, mergeStateStatus="BLOCKED")))]}
        self.fake = build_fake(
            prs=[second, first], views=views, merge={7: [blocked]},
            main_after=MAIN_PATHS | set(BETA_FILES))
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: refused by GitHub: X Pull request is not mergeable: "
                      "the base branch policy prohibits the merge. "
                      "(mergeStateStatus=BLOCKED)", out)
        merged = [a[3] for a in self.fake.argvs() if a[:3] == ("gh", "pr", "merge")]
        self.assertEqual(merged, ["7", "8"])
        self.assertEqual(len(self.fake.find("gh", "pr", "merge", "7")), 1)
        self.assertEqual(len(self.fake.find("gh", "pr", "create")), 1)

    def test_prs_are_processed_in_ascending_order(self):
        a, b = make_pr(number=9), make_pr("beta", number=8, ext="md")
        self.fake = build_fake(prs=[a, b], main_after=MAIN_PATHS | set(ALPHA_FILES + BETA_FILES))
        run_main(self.fake)
        merged = [x[3] for x in self.fake.argvs() if x[:3] == ("gh", "pr", "merge")]
        self.assertEqual(merged, ["8", "9"])

    def test_unknown_state_is_reread_then_merged(self):
        pr = make_pr(number=7)
        unknown = ok(json.dumps(dict(pr, mergeStateStatus="UNKNOWN")))
        self.fake = build_fake(prs=[pr], views={7: [unknown, unknown, ok(json.dumps(pr))]},
                               main_after=MAIN_PATHS | set(ALPHA_FILES))
        code, out, sleeps = run_main(self.fake)
        self.assertEqual(code, 0, out)
        self.assertEqual(sleeps, [2, 2])
        self.assertEqual(len(self.fake.find("gh", "pr", "merge")), 1)

    def test_state_still_unknown_after_three_reads_tries_the_merge(self):
        pr = make_pr(number=7)
        unknown = ok(json.dumps(dict(pr, mergeStateStatus="UNKNOWN")))
        self.fake = build_fake(prs=[pr], views={7: [unknown]},
                               main_after=MAIN_PATHS | set(ALPHA_FILES))
        code, _, _ = run_main(self.fake)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.fake.find("gh", "pr", "merge")), 1)


class BehindTests(OrchestrationBase):
    def behind_world(self, new_view_status="CLEAN", new_checks=None, new_oid="b" * 40,
                     main_after=None):
        pr = make_pr(number=7)
        behind = ok(json.dumps(dict(pr, mergeStateStatus="BEHIND")))
        updated = ok(json.dumps(dict(pr, headRefOid=new_oid, mergeStateStatus=new_view_status)))
        pending = ok(json.dumps([{"name": "validate-prompts (3.11)", "bucket": "pending"}]))
        green = ok(json.dumps(GREEN))
        # gate read, then first poll (old head), then polls on the new head
        views = {7: [behind, behind, updated]}
        checks = {7: [green, pending, new_checks or green]}
        return build_fake(prs=[pr], views=views, checks=checks,
                          main_after=main_after or MAIN_PATHS | set(ALPHA_FILES))

    def test_behind_updates_branch_regates_and_merges_new_sha(self):
        self.fake = self.behind_world()
        code, out, sleeps = run_main(self.fake)
        self.assertEqual(code, 0, out)
        argvs = self.fake.argvs()
        update_at = argvs.index(("gh", "pr", "update-branch", "7"))
        merge = self.fake.find("gh", "pr", "merge")[0][0]
        self.assertGreater(argvs.index(merge), update_at)
        self.assertEqual(merge[merge.index("--match-head-commit") + 1], "b" * 40)
        self.assertTrue(sleeps and set(sleeps) == {10})

    def test_behind_pr_fails_regate_on_new_head(self):
        red = [{"name": "validate-prompts (3.11)", "bucket": "fail"}]
        self.fake = self.behind_world(new_checks=ok(json.dumps(red)))
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: fails gate: checks red", out)
        self.assertEqual(self.fake.find("gh", "pr", "merge"), [])

    def test_behind_pr_that_never_gets_a_new_head_times_out(self):
        pr = make_pr(number=7)
        behind = ok(json.dumps(dict(pr, mergeStateStatus="BEHIND")))
        self.fake = build_fake(prs=[pr], views={7: [behind]})
        code, out, sleeps = run_main(self.fake)
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: timed out waiting for update-branch", out)
        self.assertEqual(len(sleeps), 60)
        self.assertEqual(self.fake.find("gh", "pr", "merge"), [])

    def test_update_branch_failure_leaves_pr_open(self):
        pr = make_pr(number=7)
        behind = ok(json.dumps(dict(pr, mergeStateStatus="BEHIND")))
        self.fake = build_fake(prs=[pr], views={7: [behind]})
        self.fake.on("gh", "pr", "update-branch", "7", responses=[(1, "", "conflict\n")])
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: update-branch failed: conflict", out)
        self.assertEqual(self.fake.find("gh", "pr", "merge"), [])


DONE_README = README.replace(
    "alpha_claude_fable_5_2_<effort>.html` | not run",
    "alpha_claude_fable_5_2_<effort>.html` | generated (high), review pending")
A, B = "a" * 40, "b" * 40


class StatusPinTests(unittest.TestCase):
    def test_description_constants(self):
        self.assertEqual(mr.STATUS_MARKER, "one-shot result exception: ")
        self.assertEqual(
            mr.RESULT_STATUS_DESC,
            "one-shot result exception: merge_results.py gate passed on this commit")
        self.assertEqual(
            mr.DOCS_STATUS_DESC,
            "one-shot result exception: merge_results.py ledger rewrite verified on "
            "this commit")
        self.assertEqual(mr.STATUS_CONTEXTS, CONTEXTS)
        for desc in (mr.RESULT_STATUS_DESC, mr.DOCS_STATUS_DESC):
            self.assertLessEqual(len(desc), 140)


class ResultStatusTests(OrchestrationBase):
    """``--post-statuses`` on result PRs: statuses only on the gated head."""

    def world(self, pr=None, views=None, checks=None, merge=None):
        pr = pr or make_pr(number=7)
        self.fake = build_fake(
            prs=[pr], views=views, checks=checks, merge=merge, readme=DONE_README,
            main_after=MAIN_PATHS | set(ALPHA_FILES), strict_api=True)
        return self.fake

    def positions(self, *prefix):
        return [i for i, argv in enumerate(self.fake.argvs()) if argv[:len(prefix)] == prefix]

    def post_positions(self):
        return [i for i, argv in enumerate(self.fake.argvs()) if status_fields(argv)]

    def behind_world(self, new_checks=None):
        pr = make_pr(number=7)
        behind = ok(json.dumps(dict(pr, mergeStateStatus="BEHIND")))
        updated = ok(json.dumps(dict(pr, headRefOid=B)))
        pending = ok(json.dumps([{"name": "validate-prompts (3.11)", "bucket": "pending"}]))
        green = ok(json.dumps(GREEN))
        return self.world(pr, views={7: [behind, behind, updated]},
                          checks={7: [green, pending, new_checks or green]})

    def test_clean_pass_posts_both_statuses_on_the_gated_head_then_merges(self):
        fake = self.world()
        script_status(fake, A)
        self.vouched = frozenset({A})
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 0, out)
        self.assertEqual(status_posts(fake), [
            (A, "orchestrai/test", mr.RESULT_STATUS_DESC),
            (A, "orchestrai/review", mr.RESULT_STATUS_DESC)])
        self.assertEqual(fake.find("gh", "api", "--method", "POST")[0][0], (
            "gh", "api", "--method", "POST", "repos/{owner}/{repo}/statuses/" + A,
            "-f", "state=success", "-f", "context=orchestrai/test",
            "-f", "description=" + mr.RESULT_STATUS_DESC))
        views = self.positions("gh", "pr", "view", "7")
        posts = self.post_positions()
        merge_at = self.positions("gh", "pr", "merge")
        self.assertEqual(len(views), 2)
        self.assertGreater(views[1], self.positions("gh", "pr", "checks", "7")[-1])
        self.assertGreater(posts[0], views[1])
        self.assertGreater(merge_at[0], posts[-1])
        merge = fake.find("gh", "pr", "merge")[0][0]
        self.assertEqual(merge[merge.index("--match-head-commit") + 1], A)
        self.assertIn("#7 merged (aaaaaaa)", out)

    def test_without_the_flag_nothing_is_posted_and_the_pr_is_read_once(self):
        fake = self.world()
        code, out, _ = run_main(fake)
        self.assertEqual(code, 0, out)
        self.assertEqual(status_posts(fake), [])
        self.assertEqual(len(fake.find("gh", "pr", "view", "7")), 1)
        self.assertEqual(len(fake.find("gh", "pr", "merge")), 1)

    def test_draft_pr_gets_no_status_and_no_merge(self):
        fake = self.world(make_pr(number=7, isDraft=True))
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: fails gate:", out)
        self.assertEqual(status_posts(fake), [])
        self.assertEqual(fake.find("gh", "pr", "merge"), [])

    def test_red_checks_get_no_status_and_no_merge(self):
        red = ok(json.dumps([{"name": "validate-prompts (3.11)", "bucket": "fail"}]))
        fake = self.world(checks={7: [red]})
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("checks red", out)
        self.assertEqual(status_posts(fake), [])
        self.assertEqual(fake.find("gh", "pr", "merge"), [])

    def test_extra_file_gets_no_status_and_no_merge(self):
        pr = make_pr(number=7, files=pr_files(*ALPHA_FILES, "results/alpha/notes.txt"))
        fake = self.world(pr)
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("extra file", out)
        self.assertEqual(status_posts(fake), [])
        self.assertEqual(fake.find("gh", "pr", "merge"), [])

    def test_behind_pr_is_vouched_only_on_the_new_head(self):
        fake = self.behind_world()
        script_status(fake, B)  # no rule for A: a post there raises
        self.vouched = frozenset({B})
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 0, out)
        self.assertEqual([sha for sha, _, _ in status_posts(fake)], [B, B])
        self.assertGreater(self.post_positions()[0],
                           self.positions("gh", "pr", "update-branch", "7")[0])
        merge = fake.find("gh", "pr", "merge")[0][0]
        self.assertEqual(merge[merge.index("--match-head-commit") + 1], B)

    def test_behind_pr_that_fails_regate_gets_no_status(self):
        red = ok(json.dumps([{"name": "validate-prompts (3.11)", "bucket": "fail"}]))
        fake = self.behind_world(new_checks=red)
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: fails gate: checks red", out)
        self.assertEqual(status_posts(fake), [])
        self.assertEqual(fake.find("gh", "pr", "merge"), [])

    def test_head_moved_after_the_gate_read_gets_no_status(self):
        pr = make_pr(number=7)
        moved = ok(json.dumps(dict(pr, headRefOid="9" * 40)))
        fake = self.world(pr, views={7: [ok(json.dumps(pr)), moved]})
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: head moved after the gate read "
                      "(aaaaaaa -> 9999999); no status posted", out)
        self.assertEqual(status_posts(fake), [])
        self.assertEqual(fake.find("gh", "pr", "merge"), [])

    def test_unreadable_confirm_read_gets_no_status(self):
        pr = make_pr(number=7)
        fake = self.world(pr, views={7: [ok(json.dumps(pr)), (1, "", "boom\n")]})
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: could not read the PR to confirm its head; "
                      "no status posted", out)
        self.assertEqual(status_posts(fake), [])
        self.assertEqual(fake.find("gh", "pr", "merge"), [])

    def test_failed_test_status_stops_before_review_and_merge(self):
        fake = self.world()
        script_status(fake, A, test=[(1, "", "HTTP 422: Validation Failed\n")])
        self.vouched = frozenset({A})
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: status post failed: orchestrai/test on aaaaaaa: "
                      "HTTP 422: Validation Failed", out)
        self.assertEqual([c for _, c, _ in status_posts(fake)], ["orchestrai/test"])
        self.assertEqual(fake.find("gh", "pr", "merge"), [])

    def test_failed_review_status_is_reported_without_retry_or_merge(self):
        fake = self.world()
        script_status(fake, A, review=[(1, "", "HTTP 500\n")])
        self.vouched = frozenset({A})
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("#7 left open: status post failed: orchestrai/review on aaaaaaa: "
                      "HTTP 500 (orchestrai/test already posted)", out)
        self.assertEqual([c for _, c, _ in status_posts(fake)],
                         ["orchestrai/test", "orchestrai/review"])
        self.assertEqual(fake.find("gh", "pr", "merge"), [])

    def test_a_failed_pr_does_not_stop_the_next_one(self):
        first = make_pr(number=7, isDraft=True)
        second = make_pr("beta", number=8, ext="md", headRefOid=B)
        readme = DONE_README.replace(
            "beta_claude_fable_5_2_<effort>.md` | not run",
            "beta_claude_fable_5_2_<effort>.md` | generated (high), review pending")
        self.fake = build_fake(prs=[first, second], readme=readme,
                               main_after=MAIN_PATHS | set(BETA_FILES), strict_api=True)
        script_status(self.fake, B)
        self.vouched = frozenset({B})
        code, out, _ = run_main(self.fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertEqual([sha for sha, _, _ in status_posts(self.fake)], [B, B])
        self.assertEqual(len(self.fake.find("gh", "pr", "merge", "8")), 1)


class ResultStatusDryRunTests(OrchestrationBase):
    def dry(self, *prs):
        self.fake = build_fake(prs=list(prs), strict_api=True)
        code, out, _ = run_main(self.fake, "--post-statuses", "--dry-run")
        self.assertEqual(self.fake.writes(), [])
        self.assertEqual(status_posts(self.fake), [])
        return code, out

    def test_clean_pr_would_be_vouched_then_merged(self):
        code, out = self.dry(make_pr(number=7))
        self.assertEqual(code, 0, out)
        self.assertIn("#7 would post orchestrai/test and orchestrai/review on aaaaaaa, "
                      "then merge (mergeStateStatus=CLEAN)\n", out)

    def test_blocked_pr_is_planned_instead_of_the_refusal_note(self):
        code, out = self.dry(make_pr(number=7, mergeStateStatus="BLOCKED"))
        self.assertIn("#7 would post orchestrai/test and orchestrai/review on aaaaaaa, "
                      "then merge (mergeStateStatus=BLOCKED)\n", out)
        self.assertNotIn("would likely be refused", out)

    def test_behind_pr_would_be_updated_and_regated_first(self):
        code, out = self.dry(make_pr(number=7, mergeStateStatus="BEHIND"))
        self.assertIn("#7 would update branch, re-gate the new head, post orchestrai/test "
                      "and orchestrai/review on it, then merge (mergeStateStatus=BEHIND)\n",
                      out)

    def test_failing_pr_would_get_no_statuses(self):
        code, out = self.dry(make_pr(number=7, isDraft=True))
        self.assertEqual(code, 1)
        self.assertRegex(out, r"(?m)^#7 fails gate: .*draft.*; no statuses would be posted$")

    def test_without_the_flag_dry_run_lines_are_unchanged(self):
        self.fake = build_fake(prs=[make_pr(number=7, mergeStateStatus="BLOCKED")])
        code, out, _ = run_main(self.fake, "--dry-run")
        self.assertIn("#7 would merge (mergeStateStatus=BLOCKED: merge would likely be "
                      "refused)\n", out)
        self.assertNotIn("statuses", out)


class DryRunTests(OrchestrationBase):
    def test_dry_run_makes_no_writes(self):
        pr = make_pr(number=7)
        self.fake = build_fake(prs=[pr])
        code, out, _ = run_main(self.fake, "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.fake.writes(), [])
        self.assertIn("#7 would merge (mergeStateStatus=CLEAN)", out)
        self.assertIn("would open a docs PR", out)
        self.assertIn("game-alpha", out)

    def test_dry_run_reports_behind_and_blocked(self):
        behind = make_pr(number=7, mergeStateStatus="BEHIND")
        blocked = make_pr("beta", number=8, ext="md", mergeStateStatus="BLOCKED")
        self.fake = build_fake(prs=[behind, blocked])
        code, out, _ = run_main(self.fake, "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("#7 would update branch, then merge", out)
        self.assertIn("#8 would merge (mergeStateStatus=BLOCKED: merge would likely be refused)", out)
        self.assertEqual(self.fake.writes(), [])

    def test_dry_run_lists_gate_failures(self):
        self.fake = build_fake(prs=[make_pr(number=7, isDraft=True)])
        code, out, _ = run_main(self.fake, "--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("#7 fails gate:", out)
        self.assertEqual(self.fake.writes(), [])

    def test_dry_run_nothing_to_do(self):
        self.fake = build_fake()
        code, out, _ = run_main(self.fake, "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("nothing to merge; ledger up to date", out)


class DocsPrTests(OrchestrationBase):
    def test_existing_ledger_pr_for_model_blocks_a_second_one(self):
        existing = [{"number": 31, "title": "docs", "isDraft": False,
                     "isCrossRepository": False,
                     "headRefName": "docs/ledger-claude-fable-5-2-abc1234"}]
        self.fake = build_fake(main_before=MAIN_PATHS | set(ALPHA_FILES), extra_list=existing)
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0, out)
        self.assertIn("ledger PR #31 already open; merge it, then re-run", out)
        self.assertEqual(self.fake.writes(), [])

    def test_rows_already_updated_need_no_docs_pr(self):
        done = README.replace("alpha_claude_fable_5_2_<effort>.html` | not run",
                              "alpha_claude_fable_5_2_<effort>.html` | generated (high), review pending")
        self.fake = build_fake(main_before=MAIN_PATHS | set(ALPHA_FILES), readme=done)
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0)
        self.assertIn("nothing to merge; ledger up to date", out)
        self.assertEqual(self.fake.writes(), [])

    def test_sidecar_missing_is_reported_and_no_pr_opened(self):
        self.fake = build_fake(main_before=MAIN_PATHS | {ALPHA_FILES[0]})
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0)
        self.assertIn("high not listed: sidecar missing", out)
        self.assertEqual(self.fake.writes(), [])

    def test_docs_pr_is_never_merged(self):
        self.fake = build_fake(main_before=MAIN_PATHS | set(ALPHA_FILES))
        code, _, _ = run_main(self.fake)
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.find("gh", "pr", "merge"), [])


class GitBlobShaTests(unittest.TestCase):
    def test_pins_match_git_hash_object(self):
        self.assertEqual(mr.git_blob_sha(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")
        self.assertEqual(mr.git_blob_sha(b"hello\n"),
                         "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_agrees_with_the_independent_test_helper(self):
        data = README.encode("utf-8")
        self.assertEqual(mr.git_blob_sha(data), blob_sha(data))


DOCS_MAIN = MAIN_PATHS | set(ALPHA_FILES)
DOCS_NEW = rewrite(main_paths=DOCS_MAIN)[0]
DOCS_PAGE = expected_page(DOCS_MAIN)  # the dashboard of the results at MAIN_SHA
DOCS_BRANCH = "docs/ledger-claude-fable-5-2-" + MAIN_SHA[:7]
DOCS_TITLE = "docs(readme): mark 1 claude-fable-5-2 ledger rows generated"
DOCS_TITLE_BOTH = DOCS_TITLE + ", regenerate dashboard"
DOCS_TITLE_DASHBOARD = "docs(dashboard): regenerate dashboard.html from main"


def file_entry(name, data, status="modified"):
    """A ``files[]`` entry of the commits API for ``name`` with content ``data``."""
    return {"filename": name, "status": status, "sha": blob_sha(data)}


README_ENTRY = file_entry("README.md", DOCS_NEW.encode("utf-8"))
DASHBOARD_ENTRY = file_entry("dashboard.html", DOCS_PAGE)
DOCS_CHANGES = {"README.md": DOCS_NEW.encode("utf-8"), "dashboard.html": DOCS_PAGE}


def make_docs_pr(number=99, **overrides):
    pr = {"number": number, "title": DOCS_TITLE, "headRefName": DOCS_BRANCH,
          "headRefOid": D, "isDraft": False, "isCrossRepository": False,
          "mergeStateStatus": "CLEAN", "files": []}
    pr.update(overrides)
    return pr


def docs_commit(parents=(MAIN_SHA,), files=None):
    """The commits API payload of a docs PR head; README.md alone unless ``files`` says more."""
    if files is None:
        files = [README_ENTRY]
    return {"sha": D, "parents": [{"sha": p} for p in parents], "files": files}


def docs_listing(*numbers, branch=DOCS_BRANCH):
    return [{"number": n, "title": DOCS_TITLE, "headRefName": branch, "isDraft": False,
             "isCrossRepository": False} for n in numbers]


class DocsStatusTests(OrchestrationBase):
    """``--post-statuses`` on the ledger docs PR: merged only when verified."""

    vouched = frozenset({A, D})

    def script_docs(self, fake, pr=None, commit=None, checks=None, merge=None, statuses=True):
        pr = pr or make_docs_pr()
        n = str(pr["number"])
        fake.on("gh", "pr", "view", n, "--json", VIEW_FIELDS, responses=[ok(json.dumps(pr))])
        fake.on("gh", "pr", "checks", n, "--json", "name,bucket",
                responses=checks or [ok(json.dumps(GREEN))])
        fake.on("gh", "api", "repos/{owner}/{repo}/commits/" + pr["headRefOid"],
                responses=[ok(json.dumps(commit or docs_commit()))])
        fake.on("gh", "pr", "merge", n, responses=merge or [ok()])
        if statuses:
            script_status(fake, pr["headRefOid"])

    def fresh(self, world=None, **kw):
        """A result PR merges, then this run opens docs PR #99 (create prints its URL)."""
        self.fake = build_fake(prs=[make_pr(number=7)], main_after=DOCS_MAIN, strict_api=True,
                               **(world or {}))
        script_status(self.fake, A)
        self.script_docs(self.fake, **kw)
        return self.fake

    def rerun(self, listed=(99,), world=None, **kw):
        """No result PRs open; docs PR(s) from an earlier run are still open."""
        self.fake = build_fake(main_before=DOCS_MAIN, strict_api=True,
                               extra_list=docs_listing(*listed), **(world or {}))
        self.script_docs(self.fake, **kw)
        return self.fake

    def docs_merge(self, fake):
        return [argv for argv in fake.argvs() if argv[:4] == ("gh", "pr", "merge", "99")]

    def docs_posts(self, fake):
        return [p for p in status_posts(fake) if p[0] == D]

    def assert_left_open(self, fake, code, out, fragment):
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^ledger PR #99 left open: .*%s" % fragment)
        self.assertEqual(self.docs_posts(fake), [])
        self.assertEqual(self.docs_merge(fake), [])
        self.assertEqual(fake.find("gh", "pr", "update-branch", "99"), [])

    def test_new_docs_pr_is_verified_vouched_and_merged(self):
        fake = self.fresh()
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.docs_posts(fake), [
            (D, "orchestrai/test", mr.DOCS_STATUS_DESC),
            (D, "orchestrai/review", mr.DOCS_STATUS_DESC)])
        self.assertEqual(self.docs_merge(fake), [(
            "gh", "pr", "merge", "99", "--squash", "--match-head-commit", D,
            "--subject", "docs(readme): mark 1 claude-fable-5-2 ledger rows generated (#99)")])
        self.assertIn("docs PR opened: https://github.com/o/r/pull/99", out)
        self.assertIn("docs PR #99 merged (eeeeeee)", out)
        self.assertEqual(fake.find("gh", "pr", "update-branch", "99"), [])
        argvs = fake.argvs()
        merge_at = argvs.index(self.docs_merge(fake)[0])
        posts = [i for i, a in enumerate(argvs) if status_fields(a) and
                 status_fields(a)["sha"] == D]
        views = [i for i, a in enumerate(argvs) if a[:4] == ("gh", "pr", "view", "99")]
        commit_at = argvs.index(("gh", "api", "repos/{owner}/{repo}/commits/" + D))
        checks = [i for i, a in enumerate(argvs) if a[:4] == ("gh", "pr", "checks", "99")]
        create_at = argvs.index(fake.find("gh", "pr", "create")[0][0])
        self.assertLess(create_at, views[0])
        self.assertLess(views[0], commit_at)
        self.assertLess(commit_at, checks[0])
        self.assertLess(checks[-1], views[-1])
        self.assertLess(views[-1], posts[0])
        self.assertLess(posts[-1], merge_at)

    def test_checks_still_pending_are_polled_before_the_merge(self):
        pending = ok(json.dumps([{"name": "validate-prompts (3.11)", "bucket": "pending"}]))
        fake = self.fresh(checks=[ok("[]"), pending, ok(json.dumps(GREEN))])
        code, out, sleeps = run_main(fake, "--post-statuses")
        self.assertEqual(code, 0, out)
        self.assertEqual(sleeps, [10, 10])
        self.assertEqual(len(self.docs_merge(fake)), 1)

    def test_docs_pr_from_an_earlier_run_is_verified_vouched_and_merged(self):
        fake = self.rerun()
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.docs_posts(fake)), 2)
        self.assertEqual(len(self.docs_merge(fake)), 1)
        self.assertEqual(fake.find("gh", "pr", "create"), [])
        self.assertEqual(fake.find(*post_argv("git/refs")), [])
        self.assertIn("docs PR #99 merged (eeeeeee)", out)

    def test_extra_file_keeps_the_docs_pr_open(self):
        files = docs_commit()["files"] + [
            {"filename": "results/x.md", "status": "added", "sha": "1" * 40}]
        fake = self.fresh(commit=docs_commit(files=files), statuses=False)
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "fails docs gate: .*extra file: 'results/x.md'")

    def test_an_extra_file_name_cannot_fake_a_merged_line_in_the_output(self):
        name = "x.md\ndocs PR #99 merged (eeeeeee)"
        files = docs_commit()["files"] + [{"filename": name, "status": "added", "sha": "1" * 40}]
        fake = self.fresh(commit=docs_commit(files=files), statuses=False)
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "fails docs gate: .*extra file: 'x.md")
        self.assertEqual(len(re.findall(r"(?m)^ledger PR #99 left open", out)), 1, out)
        self.assertNotRegex(out, r"(?m)^docs PR #99 merged")

    def test_wrong_readme_blob_keeps_the_docs_pr_open(self):
        files = [{"filename": "README.md", "status": "modified", "sha": "1" * 40}]
        fake = self.fresh(commit=docs_commit(files=files), statuses=False)
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out,
                              "fails docs gate: .*README.md blob is not this run's content")

    def test_stale_parent_keeps_the_docs_pr_open(self):
        fake = self.rerun(commit=docs_commit(parents=("f" * 40,)), statuses=False)
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "fails docs gate: .*; close it and re-run$")

    def test_merge_commit_head_keeps_the_docs_pr_open(self):
        fake = self.rerun(commit=docs_commit(parents=(MAIN_SHA, "f" * 40)), statuses=False)
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "fails docs gate: .*parent")

    def test_base_readme_that_differs_from_main_keeps_the_docs_pr_open(self):
        fake = self.fresh(statuses=False)
        fake.on("git", "rev-parse", PIN + "README.md", responses=[ok("1" * 40 + "\n")])
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "fails docs gate: .*base README")

    def test_wrong_branch_name_keeps_the_docs_pr_open(self):
        fake = self.fresh(pr=make_docs_pr(headRefName="docs/ledger-claude-fable-5-2-zzzzzzz"),
                          statuses=False)
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "fails docs gate: .*branch")

    def test_red_checks_keep_the_docs_pr_open(self):
        red = ok(json.dumps([{"name": "validate-prompts (3.11)", "bucket": "fail"}]))
        fake = self.fresh(checks=[red], statuses=False)
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "checks red")

    def test_checks_that_never_finish_keep_the_docs_pr_open(self):
        pending = ok(json.dumps([{"name": "validate-prompts (3.11)", "bucket": "pending"}]))
        fake = self.fresh(checks=[pending], statuses=False)
        code, out, sleeps = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "timed out waiting for checks")
        self.assertEqual(len(sleeps), mr.POLL_LIMIT - 1)

    def test_head_that_moves_before_the_posts_keeps_the_docs_pr_open(self):
        fake = self.fresh(statuses=False)
        moved = ok(json.dumps(make_docs_pr(headRefOid="9" * 40)))
        fake.on("gh", "pr", "view", "99", "--json", VIEW_FIELDS,
                responses=[ok(json.dumps(make_docs_pr())), moved])
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "head moved after the gate read")

    # -- the two-file proof ---------------------------------------------------

    BOTH = [README_ENTRY, DASHBOARD_ENTRY]

    def test_new_two_file_docs_pr_is_verified_vouched_and_merged(self):
        fake = self.fresh(world={"dashboard_on_main": "before"},
                          pr=make_docs_pr(title=DOCS_TITLE_BOTH),
                          commit=docs_commit(files=self.BOTH))
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.docs_posts(fake)), 2)
        self.assertEqual(self.docs_merge(fake), [(
            "gh", "pr", "merge", "99", "--squash", "--match-head-commit", D, "--subject",
            DOCS_TITLE_BOTH + " (#99)")])
        self.assertEqual(fake.find("gh", "pr", "update-branch", "99"), [])

    def test_new_dashboard_only_docs_pr_is_verified_vouched_and_merged(self):
        self.fake = build_fake(main_before=DOCS_MAIN, readme=DONE_README, strict_api=True,
                               dashboard_on_main="stale")
        self.script_docs(self.fake, pr=make_docs_pr(title=DOCS_TITLE_DASHBOARD),
                         commit=docs_commit(files=[DASHBOARD_ENTRY]))
        code, out, _ = run_main(self.fake, "--post-statuses")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.docs_posts(self.fake)), 2)
        self.assertEqual(self.docs_merge(self.fake), [(
            "gh", "pr", "merge", "99", "--squash", "--match-head-commit", D, "--subject",
            DOCS_TITLE_DASHBOARD + " (#99)")])
        self.assertEqual(len(self.fake.find(*post_argv("git/blobs"))), 1)  # the page only

    def test_two_file_pr_from_an_earlier_run_is_verified_vouched_and_merged(self):
        fake = self.rerun(world={"dashboard_on_main": "stale"},
                          commit=docs_commit(files=self.BOTH))
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.docs_merge(fake)), 1)
        self.assertEqual(len(self.docs_posts(fake)), 2)

    def test_earlier_one_file_pr_still_merges_when_the_dashboard_is_current(self):
        fake = self.rerun(world={"dashboard_on_main": "current"})
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.docs_merge(fake)), 1)

    def test_earlier_one_file_pr_stays_open_when_the_dashboard_is_stale_too(self):
        fake = self.rerun(world={"dashboard_on_main": "stale"}, statuses=False)
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "fails docs gate: .*missing: dashboard.html")

    def test_two_file_pr_stays_open_when_only_the_readme_is_expected(self):
        fake = self.rerun(world={"dashboard_on_main": "current"}, statuses=False,
                          commit=docs_commit(files=self.BOTH))
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "fails docs gate: .*extra file: 'dashboard.html'")

    def test_a_third_file_keeps_the_two_file_pr_open(self):
        files = self.BOTH + [{"filename": "results/x.md", "status": "added", "sha": "1" * 40}]
        fake = self.fresh(world={"dashboard_on_main": "before"}, statuses=False,
                          commit=docs_commit(files=files))
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "fails docs gate: .*extra file: 'results/x.md'")

    def test_wrong_dashboard_content_keeps_the_two_file_pr_open(self):
        files = [README_ENTRY, file_entry("dashboard.html", b"<html>edited by hand</html>")]
        fake = self.fresh(world={"dashboard_on_main": "before"}, statuses=False,
                          commit=docs_commit(files=files))
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(
            fake, code, out, "fails docs gate: .*dashboard.html blob is not this run's content")

    def test_a_dashboard_not_built_from_this_runs_results_keeps_the_pr_open(self):
        # The PR carries the page of the results before the merge: stale by one result.
        stale = file_entry("dashboard.html", expected_page(MAIN_PATHS))
        fake = self.fresh(world={"dashboard_on_main": "before"}, statuses=False,
                          commit=docs_commit(files=[README_ENTRY, stale]))
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "dashboard.html blob is not this run's content")

    def test_dashboard_that_is_not_modified_keeps_the_pr_open(self):
        files = [README_ENTRY, dict(DASHBOARD_ENTRY, status="added")]
        fake = self.fresh(world={"dashboard_on_main": "before"}, statuses=False,
                          commit=docs_commit(files=files))
        code, out, _ = run_main(fake, "--post-statuses")
        self.assert_left_open(fake, code, out, "dashboard.html status is 'added'")

    def test_without_the_flag_a_two_file_pr_is_opened_and_never_merged_or_vouched(self):
        self.vouched = frozenset({A})
        self.fake = build_fake(prs=[make_pr(number=7)], main_after=DOCS_MAIN, strict_api=True,
                               dashboard_on_main="before")
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.fake.find("gh", "pr", "create")), 1)
        self.assertEqual(len(self.fake.find("gh", "pr", "merge")), 1)  # the result PR only
        self.assertEqual(status_posts(self.fake), [])
        self.assertEqual(self.fake.find("gh", "pr", "view", "99"), [])

    def test_two_open_docs_prs_stay_open_without_statuses(self):
        self.fake = build_fake(main_before=DOCS_MAIN, strict_api=True,
                               extra_list=docs_listing(98, 99))
        code, out, _ = run_main(self.fake, "--post-statuses")
        self.assertEqual(code, 1, out)
        self.assertIn("ledger PRs #98, #99 are open; no statuses posted; "
                      "close all but one and re-run", out)
        self.assertEqual(status_posts(self.fake), [])
        self.assertEqual(self.fake.find("gh", "pr", "merge"), [])
        self.assertEqual(self.fake.find("gh", "pr", "view"), [])

    def test_unreadable_pr_number_leaves_the_new_docs_pr_open(self):
        self.fake = build_fake(prs=[make_pr(number=7)], main_after=DOCS_MAIN, strict_api=True)
        script_status(self.fake, A)
        self.fake.on("gh", "pr", "create", responses=[ok("created it\n")])
        code, out, _ = run_main(self.fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("ledger PR left open: could not read its number from: created it", out)
        self.assertEqual([p for p in status_posts(self.fake) if p[0] != A], [])

    def test_failed_docs_status_post_means_no_merge(self):
        fake = self.fresh(statuses=False)
        script_status(fake, D, test=[(1, "", "HTTP 403\n")])
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("ledger PR #99 left open: status post failed: orchestrai/test on "
                      "eeeeeee: HTTP 403", out)
        self.assertEqual(len(self.docs_posts(fake)), 1)
        self.assertEqual(self.docs_merge(fake), [])

    def test_refused_docs_merge_exits_1(self):
        fake = self.fresh(merge=[(1, "", "X Pull request is not mergeable\n")])
        code, out, _ = run_main(fake, "--post-statuses")
        self.assertEqual(code, 1)
        self.assertIn("ledger PR #99 left open: refused by GitHub: "
                      "X Pull request is not mergeable", out)
        self.assertEqual(len(self.docs_merge(fake)), 1)
        self.assertEqual(len(self.docs_posts(fake)), 2)

    def test_without_the_flag_the_docs_pr_is_still_never_touched(self):
        self.vouched = frozenset({A})
        self.fake = build_fake(prs=[make_pr(number=7)], main_after=DOCS_MAIN, strict_api=True)
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0, out)
        self.assertEqual(status_posts(self.fake), [])
        self.assertEqual(len(self.fake.find("gh", "pr", "merge")), 1)
        self.assertEqual(self.fake.find("gh", "pr", "view", "99"), [])

    def test_without_the_flag_an_open_docs_pr_still_exits_0(self):
        self.fake = build_fake(main_before=DOCS_MAIN, extra_list=docs_listing(31))
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0, out)
        self.assertIn("ledger PR #31 already open; merge it, then re-run", out)


class DocsGateTests(unittest.TestCase):
    """The pure proof, over the expected file set E (README.md, dashboard.html, or both)."""

    README_ONLY = {"README.md": DOCS_CHANGES["README.md"]}
    DASHBOARD_ONLY = {"dashboard.html": DOCS_PAGE}
    SHAPES = {"both": (DOCS_CHANGES, [README_ENTRY, DASHBOARD_ENTRY]),
              "README only": (README_ONLY, [README_ENTRY]),
              "dashboard only": (DASHBOARD_ONLY, [DASHBOARD_ENTRY])}

    def gate(self, pr=None, commit=None, main_sha=MAIN_SHA, main_blob=None, text=README,
             changes=None, dashboard_sha=MAIN_SHA):
        return mr.docs_gate(pr or make_docs_pr(), commit or docs_commit(files=[
            README_ENTRY, DASHBOARD_ENTRY]), main_sha,
            main_blob or blob_sha(text.encode("utf-8")), text,
            DOCS_CHANGES if changes is None else changes, dashboard_sha, TAG)

    def shape(self, name, **kw):
        changes, files = self.SHAPES[name]
        return self.gate(commit=kw.pop("commit", None) or docs_commit(files=files),
                         changes=changes, **kw)

    def assertReason(self, reasons, fragment):
        self.assertTrue(any(fragment in r for r in reasons), (fragment, reasons))

    def test_each_of_the_three_exact_shapes_passes(self):
        for name in self.SHAPES:
            with self.subTest(shape=name):
                self.assertEqual(self.shape(name), [])

    def test_draft_and_fork_are_refused(self):
        for name in self.SHAPES:
            with self.subTest(shape=name):
                reasons = self.shape(name, pr=make_docs_pr(isDraft=True, isCrossRepository=True))
                self.assertReason(reasons, "draft")
                self.assertReason(reasons, "fork")

    def test_a_third_file_is_refused_in_every_shape(self):
        extra = {"filename": "notes.md", "status": "added", "sha": "1" * 40}
        for name, (_, files) in self.SHAPES.items():
            with self.subTest(shape=name):
                reasons = self.shape(name, commit=docs_commit(files=files + [extra]))
                self.assertReason(reasons, "extra file: 'notes.md'")

    def test_the_other_expected_file_is_an_extra_file(self):
        self.assertReason(self.shape("README only", commit=docs_commit(
            files=[README_ENTRY, DASHBOARD_ENTRY])), "extra file: 'dashboard.html'")
        self.assertReason(self.shape("dashboard only", commit=docs_commit(
            files=[README_ENTRY, DASHBOARD_ENTRY])), "extra file: 'README.md'")

    def test_an_extra_file_name_is_quoted_so_it_cannot_fake_output_lines(self):
        names = ["x\nledger PR #99 merged", "\x1b[2Kx", "a\rb", "\u2028"]
        for name in names:
            with self.subTest(name=name):
                extra = {"filename": name, "status": "added", "sha": "1" * 40}
                reasons = self.shape("both", commit=docs_commit(
                    files=[README_ENTRY, DASHBOARD_ENTRY, extra]))
                self.assertEqual(reasons, ["extra file: %r" % name])
                for char in ("\n", "\r", "\x1b", "\u2028"):
                    self.assertFalse(any(char in r for r in reasons), (char, reasons))

    def test_a_missing_filename_in_the_api_answer_is_still_an_extra_file(self):
        extra = {"status": "added", "sha": "1" * 40}
        reasons = self.shape("both", commit=docs_commit(
            files=[README_ENTRY, DASHBOARD_ENTRY, extra]))
        self.assertEqual(reasons, ["extra file: None"])

    def test_an_expected_file_that_is_absent_is_missing(self):
        self.assertReason(self.shape("both", commit=docs_commit(files=[README_ENTRY])),
                          "missing: dashboard.html")
        self.assertReason(self.shape("both", commit=docs_commit(files=[DASHBOARD_ENTRY])),
                          "missing: README.md")
        self.assertReason(self.shape("README only", commit=docs_commit(files=[])),
                          "missing: README.md")
        self.assertReason(self.shape("dashboard only", commit=docs_commit(files=[])),
                          "missing: dashboard.html")

    def test_wrong_content_in_either_file_is_refused(self):
        wrong = file_entry("README.md", b"something else")
        self.assertReason(self.shape("both", commit=docs_commit(
            files=[wrong, DASHBOARD_ENTRY])), "README.md blob is not this run's content")
        wrong = file_entry("dashboard.html", b"something else")
        self.assertReason(self.shape("both", commit=docs_commit(
            files=[README_ENTRY, wrong])), "dashboard.html blob is not this run's content")
        self.assertReason(self.shape("dashboard only", commit=docs_commit(
            files=[wrong])), "dashboard.html blob is not this run's content")

    def test_a_status_other_than_modified_is_refused_for_either_file(self):
        for status in ("added", "removed", "renamed", None):
            with self.subTest(status=status):
                readme = dict(README_ENTRY, status=status)
                dash = dict(DASHBOARD_ENTRY, status=status)
                self.assertReason(self.shape("both", commit=docs_commit(
                    files=[readme, DASHBOARD_ENTRY])), "README.md status is")
                self.assertReason(self.shape("both", commit=docs_commit(
                    files=[README_ENTRY, dash])), "dashboard.html status is")

    def test_a_file_listed_twice_is_refused(self):
        self.assertReason(self.shape("both", commit=docs_commit(
            files=[README_ENTRY, DASHBOARD_ENTRY, README_ENTRY])),
            "README.md listed more than once")
        self.assertReason(self.shape("dashboard only", commit=docs_commit(
            files=[DASHBOARD_ENTRY, DASHBOARD_ENTRY])), "dashboard.html listed more than once")

    def test_entries_without_a_file_name_are_an_extra_file(self):
        self.assertReason(self.shape("README only", commit=docs_commit(
            files=[README_ENTRY, {"status": "modified", "sha": "1" * 40}])), "extra file")

    def test_parent_must_be_exactly_the_pinned_main(self):
        for parents in (("f" * 40,), (MAIN_SHA, "f" * 40), ()):
            with self.subTest(parents=parents):
                self.assertReason(self.shape("both", commit=docs_commit(
                    parents=parents, files=[README_ENTRY, DASHBOARD_ENTRY])), "parent")

    def test_text_that_is_not_main_s_readme_is_refused_when_readme_is_in_the_set(self):
        self.assertReason(self.shape("both", main_blob="1" * 40), "base README")
        self.assertReason(self.shape("README only", main_blob="1" * 40), "base README")

    def test_the_base_readme_is_not_checked_when_only_the_dashboard_changes(self):
        self.assertEqual(self.shape("dashboard only", main_blob="1" * 40), [])

    def test_the_dashboard_must_have_been_computed_from_the_pinned_main(self):
        self.assertReason(self.shape("both", dashboard_sha="f" * 40), "dashboard.html")
        self.assertReason(self.shape("dashboard only", dashboard_sha="f" * 40), "computed from")
        # Not in the set: its source does not matter.
        self.assertEqual(self.shape("README only", dashboard_sha="f" * 40), [])

    def test_a_name_outside_the_two_files_can_never_be_in_the_set(self):
        reasons = self.gate(changes={"README.md": DOCS_CHANGES["README.md"],
                                     "notes.md": b"x"},
                            commit=docs_commit(files=[README_ENTRY]))
        self.assertReason(reasons, "notes.md")

    def test_branch_must_name_this_model_and_a_short_sha_in_every_shape(self):
        for shape in self.SHAPES:
            for name in ("docs/ledger-claude-fable-5-2-abc123", "docs/ledger-other-abcdef1",
                         "docs/ledger-claude-fable-5-2-abcdef12", "feat/1-x"):
                with self.subTest(shape=shape, name=name):
                    self.assertReason(
                        self.shape(shape, pr=make_docs_pr(headRefName=name)), "branch")

    def test_every_failure_is_collected(self):
        reasons = self.gate(pr=make_docs_pr(isDraft=True), main_blob="1" * 40,
                            commit=docs_commit(parents=("f" * 40,), files=[
                                file_entry("README.md", b"x", status="added"),
                                file_entry("notes.md", b"y")]))
        for fragment in ("draft", "base README", "parent", "extra file: 'notes.md'",
                         "missing: dashboard.html", "README.md status is",
                         "README.md blob is not"):
            self.assertReason(reasons, fragment)

    def test_gate_never_touches_the_inputs(self):
        changes = dict(DOCS_CHANGES)
        self.gate(changes=changes)
        self.assertEqual(changes, DOCS_CHANGES)

    def test_branch_must_name_this_model_and_a_short_sha(self):
        for name in ("docs/ledger-claude-fable-5-2-abc123", "docs/ledger-other-abcdef1",
                     "docs/ledger-claude-fable-5-2-abcdef12", "feat/1-x"):
            with self.subTest(name=name):
                self.assertReason(self.gate(pr=make_docs_pr(headRefName=name)), "branch")


class DocsStatusDryRunTests(OrchestrationBase):
    def dry(self, **kw):
        self.fake = build_fake(main_before=DOCS_MAIN, strict_api=True, **kw)
        code, out, _ = run_main(self.fake, "--post-statuses", "--dry-run")
        self.assertEqual(self.fake.writes(), [])
        self.assertEqual(status_posts(self.fake), [])
        return code, out

    def test_new_docs_pr_would_be_vouched_and_merged_once_verified(self):
        code, out = self.dry()
        self.assertEqual(code, 0, out)
        self.assertIn(
            "would open a docs PR marking 1 row(s) generated, then post orchestrai/test and "
            "orchestrai/review on it and merge it once its diff is verified and its checks "
            "are green\n", out)

    def test_open_docs_pr_would_be_vouched_only_if_it_is_exactly_the_rewrite(self):
        code, out = self.dry(extra_list=docs_listing(99))
        self.assertEqual(code, 0, out)
        self.assertIn(
            "ledger PR #99 already open; would post orchestrai/test and orchestrai/review on "
            "it and merge it only if it is exactly this rewrite on origin/main and its checks "
            "are green\n", out)

    def test_two_open_docs_prs_are_reported_as_a_problem(self):
        code, out = self.dry(extra_list=docs_listing(98, 99))
        self.assertEqual(code, 1)
        self.assertIn("ledger PRs #98, #99 are open; no statuses would be posted; "
                      "close all but one and re-run", out)

    def test_without_the_flag_the_ledger_lines_are_unchanged(self):
        self.fake = build_fake(main_before=DOCS_MAIN, extra_list=docs_listing(99))
        code, out, _ = run_main(self.fake, "--dry-run")
        self.assertIn("ledger PR #99 already open; merge it, then re-run\n", out)
        self.fake = build_fake(main_before=DOCS_MAIN)
        code, out, _ = run_main(self.fake, "--dry-run")
        self.assertIn("would open a docs PR marking 1 row(s) generated\n", out)


def posts(fake):
    """``[(endpoint name, body)]`` of every git data API POST, in call order."""
    return [(argv[4].rsplit("/", 1)[1], json.loads(body)) for argv, body in fake.calls
            if argv[:4] == ("gh", "api", "--method", "POST") and argv[4].startswith(REPO_API + "git/")]


class DashboardPrTests(OrchestrationBase):
    """The docs PR carries README.md, dashboard.html or both, and none when both are current."""

    def both(self, **kw):
        # A result merges; the dashboard committed on main predates it.
        kw.setdefault("dashboard_on_main", "before")
        self.fake = build_fake(prs=[make_pr(number=7)], main_after=DOCS_MAIN, **kw)
        return self.fake

    def readme_only(self, **kw):
        self.fake = build_fake(main_before=DOCS_MAIN, **kw)  # dashboard current
        return self.fake

    def dashboard_only(self, **kw):
        kw.setdefault("dashboard_on_main", "stale")
        self.fake = build_fake(main_before=DOCS_MAIN, readme=DONE_README, **kw)
        return self.fake

    def neither(self, **kw):
        self.fake = build_fake(main_before=DOCS_MAIN, readme=DONE_README, **kw)
        return self.fake

    def assert_one_commit(self, fake, files, title):
        """The API sequence builds one commit on the pinned main with exactly ``files``."""
        made = posts(fake)
        self.assertEqual([name for name, _ in made],
                         ["blobs"] * len(files) + ["trees", "commits", "refs"])
        for (_, body), (_, data) in zip(made, files):
            self.assertEqual(body, {"content": base64.b64encode(data).decode("ascii"),
                                    "encoding": "base64"})
        self.assertEqual(made[len(files)][1], {
            "base_tree": MAIN_TREE,
            "tree": [{"path": name, "mode": "100644", "type": "blob", "sha": blob_sha(data)}
                     for name, data in files]})
        self.assertEqual(made[-2][1], {"message": title, "tree": NEW_TREE, "parents": [MAIN_SHA]})
        self.assertEqual(made[-1][1], {"ref": "refs/heads/" + DOCS_BRANCH, "sha": NEW_COMMIT})
        argvs = fake.argvs()
        last_post = max(i for i, a in enumerate(argvs) if a[:4] == ("gh", "api", "--method", "POST"))
        create_at = argvs.index(fake.find("gh", "pr", "create")[0][0])
        self.assertLess(last_post, create_at)  # the branch exists only with its commit on it
        create = argvs[create_at]
        self.assertEqual(create[create.index("--head") + 1], DOCS_BRANCH)
        self.assertEqual(create[create.index("--base") + 1], "main")
        self.assertEqual(create[create.index("--title") + 1], title)
        self.assertEqual(fake.find("gh", "api", "--method", "PUT"), [])
        self.assertEqual(fake.find("gh", "pr", "merge", "99"), [])

    def test_both_files_go_into_one_commit(self):
        fake = self.both()
        code, out, _ = run_main(fake)
        self.assertEqual(code, 0, out)
        self.assert_one_commit(fake, [("README.md", DOCS_NEW.encode("utf-8")),
                                      ("dashboard.html", DOCS_PAGE)], DOCS_TITLE_BOTH)
        self.assertIn("docs PR opened: https://github.com/o/r/pull/99", out)

    def test_ledger_only_goes_into_one_commit_with_the_readme_title(self):
        fake = self.readme_only()
        code, out, _ = run_main(fake)
        self.assertEqual(code, 0, out)
        self.assert_one_commit(fake, [("README.md", DOCS_NEW.encode("utf-8"))], DOCS_TITLE)

    def test_dashboard_only_goes_into_one_commit_with_the_dashboard_title(self):
        fake = self.dashboard_only()
        code, out, _ = run_main(fake)
        self.assertEqual(code, 0, out)
        self.assert_one_commit(fake, [("dashboard.html", DOCS_PAGE)], DOCS_TITLE_DASHBOARD)
        self.assertIn("ledger up to date", out)
        body = fake.find("gh", "pr", "create")[0][0]
        body = body[body.index("--body") + 1]
        self.assertIn("dashboard.html", body)
        self.assertNotIn("Rows:", body)

    def test_nothing_is_opened_when_ledger_and_dashboard_are_current(self):
        fake = self.neither()
        code, out, _ = run_main(fake)
        self.assertEqual(code, 0, out)
        self.assertEqual(fake.writes(), [])
        self.assertEqual(posts(fake), [])
        self.assertIn("ledger up to date", out)
        self.assertIn("dashboard.html up to date", out)

    def test_the_page_is_the_page_of_the_results_on_main_not_of_the_working_tree(self):
        # Nothing in the fake touches a disk folder: the only source of rows is the git tree.
        fake = self.dashboard_only()
        run_main(fake)
        (_, body), = posts(fake)[:1]
        page = base64.b64decode(body["content"]).decode("utf-8")
        for path in DOCS_MAIN:
            if not path.endswith(".meta.json"):
                self.assertIn(urllib.parse.quote(path, safe="/"), page)

    def test_only_sidecar_and_run_blobs_are_read_from_main(self):
        fake = self.dashboard_only()
        run_main(fake)
        entries = result_entries(DOCS_MAIN)
        sidecars = {blob_sha(c) for p, c in entries if p.endswith((b".meta.json", b".run.json"))}
        others = {blob_sha(c) for p, c in entries} - sidecars
        requests = [i for a, i in fake.calls if a == ("git", "cat-file", "--batch")]
        self.assertEqual(len(requests), 1)
        asked = set(requests[0].decode("ascii").split("\n")[:-1])
        self.assertEqual(asked, sidecars)
        self.assertTrue(others)
        self.assertFalse(asked & others)

    def test_the_two_listing_and_blob_reads_are_binary_and_every_other_call_is_text(self):
        fake = self.both()
        run_main(fake)
        self.assertEqual(set(fake.binary_argvs), {
            ("git", "ls-tree", "-r", "-z", MAIN_SHA, "--", "results"),
            ("git", "cat-file", "--batch")})

    def test_origin_main_is_resolved_once_and_every_later_read_names_the_sha(self):
        fake = self.both()
        run_main(fake)
        argvs = fake.argvs()
        resolves = [i for i, a in enumerate(argvs) if a == ("git", "rev-parse", "origin/main")]
        self.assertEqual(len(resolves), 1)
        after = [a for a in argvs[resolves[0] + 1:] if a[0] == "git"]
        self.assertTrue(after)
        for argv in after:
            self.assertFalse(any("origin/main" in part for part in argv), argv)
            if argv != ("git", "cat-file", "--batch"):  # that one is fed object ids
                self.assertIn(MAIN_SHA, " ".join(argv))
        # The new commit is the child of exactly the commit everything was read at.
        self.assertEqual(posts(fake)[-2][1]["parents"], [MAIN_SHA])

    def test_a_moved_origin_main_is_never_read_midway(self):
        fake = self.readme_only()
        fake.on("git", "rev-parse", "origin/main",
                responses=[ok(MAIN_SHA + "\n"), ok("b" * 40 + "\n")])
        code, out, _ = run_main(fake)
        self.assertEqual(code, 0, out)
        self.assertNotIn("b" * 40, " ".join(" ".join(a) for a in fake.argvs()))
        self.assertEqual(posts(fake)[-2][1]["parents"], [MAIN_SHA])

    def test_warnings_while_reading_the_results_are_counted_never_printed(self):
        fake = self.readme_only()
        entries = result_entries(DOCS_MAIN)
        broken = [(p, b"{not json" if p == b"results/alpha/alpha_other_model.meta.json" else c)
                  for p, c in entries]
        fake.on("git", "ls-tree", "-r", "-z", MAIN_SHA, "--", "results",
                responses=[okb(ls_tree_z(broken))])
        fake.on("git", "cat-file", "--batch", responses=[cat_file_reply(broken)])
        code, out, _ = run_main(fake)
        self.assertEqual(code, 0, out)
        self.assertIn("dashboard: 1 warning(s) while reading the results on origin/main; "
                      "text not shown", out)
        self.assertNotIn("alpha_other_model", out)
        self.assertNotIn("cannot read", out)

    # -- failures ---------------------------------------------------------------

    def failing(self, fake, endpoint, reply):
        fake.on(*post_argv(endpoint), responses=[reply])

    def assert_step_failed(self, code, out, fake, step, detail, leftover=False):
        self.assertEqual(code, 1, out)
        self.assertIn("docs PR step failed: %s: %s" % (step, detail), out)
        if leftover:
            self.assertIn("leftover branch: " + DOCS_BRANCH, out)
        else:
            self.assertNotIn("leftover branch", out)

    def test_a_failing_blob_call_stops_the_sequence_and_leaves_nothing_visible(self):
        for index, step in ((0, "create blob README.md"), (1, "create blob dashboard.html")):
            with self.subTest(step=step):
                fake = self.both()
                calls = []

                def reply(argv, input, index=index, calls=calls):
                    calls.append(input)
                    if len(calls) - 1 == index:
                        return (1, "", "HTTP 500\n")
                    return blob_reply(argv, input)

                self.failing(fake, "git/blobs", reply)
                code, out, _ = run_main(fake)
                self.assert_step_failed(code, out, fake, step, "HTTP 500")
                self.assertEqual([n for n, _ in posts(fake)], ["blobs"] * (index + 1))
                self.assertEqual(fake.find("gh", "pr", "create"), [])

    def test_a_blob_id_that_is_not_the_local_one_is_a_failure(self):
        fake = self.readme_only()
        self.failing(fake, "git/blobs", ok(json.dumps({"sha": "9" * 40})))
        code, out, _ = run_main(fake)
        self.assert_step_failed(code, out, fake, "create blob README.md",
                                "GitHub returned blob 9999999, expected %s" % (
                                    blob_sha(DOCS_NEW.encode("utf-8"))[:7]))
        self.assertEqual([n for n, _ in posts(fake)], ["blobs"])
        self.assertEqual(fake.find("gh", "pr", "create"), [])

    def test_an_answer_that_is_not_json_with_a_sha_is_a_failure(self):
        for reply in (ok("not json"), ok("[]"), ok("{}"), ok(json.dumps({"sha": 7}))):
            with self.subTest(reply=reply):
                fake = self.readme_only()
                self.failing(fake, "git/blobs", reply)
                code, out, _ = run_main(fake)
                self.assert_step_failed(code, out, fake, "create blob README.md",
                                        "unexpected answer")
                self.assertEqual(fake.find("gh", "pr", "create"), [])

    def test_a_failing_tree_call_leaves_nothing_visible(self):
        fake = self.both()
        self.failing(fake, "git/trees", (1, "", "HTTP 422\n"))
        code, out, _ = run_main(fake)
        self.assert_step_failed(code, out, fake, "create tree", "HTTP 422")
        self.assertEqual([n for n, _ in posts(fake)], ["blobs", "blobs", "trees"])
        self.assertEqual(fake.find("gh", "pr", "create"), [])

    def test_a_failing_commit_call_leaves_nothing_visible(self):
        fake = self.both()
        self.failing(fake, "git/commits", (1, "", "HTTP 409\n"))
        code, out, _ = run_main(fake)
        self.assert_step_failed(code, out, fake, "create commit", "HTTP 409")
        self.assertEqual([n for n, _ in posts(fake)], ["blobs", "blobs", "trees", "commits"])
        self.assertEqual(fake.find("gh", "pr", "create"), [])

    def test_a_failing_ref_call_leaves_no_branch(self):
        fake = self.both()
        self.failing(fake, "git/refs", (1, "", "HTTP 422 Reference already exists\n"))
        code, out, _ = run_main(fake)
        self.assert_step_failed(code, out, fake, "create branch",
                                "HTTP 422 Reference already exists")
        self.assertEqual(fake.find("gh", "pr", "create"), [])

    def test_a_tree_or_commit_answer_without_a_full_sha_is_a_failure(self):
        for endpoint, step in (("git/trees", "create tree"), ("git/commits", "create commit")):
            for reply in (ok("{}"), ok(json.dumps({"sha": "abc"})), ok("nope")):
                with self.subTest(step=step, reply=reply):
                    fake = self.readme_only()
                    self.failing(fake, endpoint, reply)
                    code, out, _ = run_main(fake)
                    self.assert_step_failed(code, out, fake, step, "unexpected answer")
                    self.assertEqual(fake.find(*post_argv("git/refs")), [])

    def test_a_failing_pr_create_names_the_leftover_branch(self):
        fake = self.both()
        fake.on("gh", "pr", "create", responses=[(1, "", "HTTP 502\n")])
        code, out, _ = run_main(fake)
        self.assert_step_failed(code, out, fake, "open PR", "HTTP 502", leftover=True)
        self.assertEqual([n for n, _ in posts(fake)],
                         ["blobs", "blobs", "trees", "commits", "refs"])

    def test_unreadable_origin_main_exits_1_and_writes_nothing(self):
        cases = {
            "resolve": (("git", "rev-parse", "origin/main"), (128, "", "fatal: bad revision\n"),
                        "could not resolve origin/main: fatal: bad revision"),
            "garbage sha": (("git", "rev-parse", "origin/main"), ok("not a sha\n"),
                            "could not resolve origin/main"),
            "tree": (("git", "rev-parse", MAIN_SHA + "^{tree}"), (128, "", "fatal: nope\n"),
                     "could not read the tree of origin/main: fatal: nope"),
            "README": (("git", "show", PIN + "README.md"), (128, "", "fatal: no README\n"),
                       "could not read README.md from origin/main: fatal: no README"),
            "README blob": (("git", "rev-parse", PIN + "README.md"), (128, "", "fatal: no blob\n"),
                            "could not read README.md from origin/main: fatal: no blob"),
            "listing": (("git", "ls-tree", "-r", "-z", MAIN_SHA, "--", "results"),
                        (128, b"", b"fatal: not a tree object\xff\n"),
                        "could not read the results on origin/main: git ls-tree failed: "
                        "fatal: not a tree object�"),
            "listing shape": (("git", "ls-tree", "-r", "-z", MAIN_SHA, "--", "results"),
                              okb(b"junk\0"), "could not read the results on origin/main: "
                              "unexpected git ls-tree output"),
            "blobs": (("git", "cat-file", "--batch"), okb(b"junk\n"),
                      "could not read the results on origin/main: unexpected git cat-file output"),
        }
        for name, (prefix, reply, message) in cases.items():
            with self.subTest(case=name):
                fake = self.both()
                fake.on(*prefix, responses=[reply])
                code, out, _ = run_main(fake)
                self.assertEqual(code, 1, out)
                self.assertIn(message, out)
                self.assertEqual(posts(fake), [])
                self.assertEqual(fake.find("gh", "pr", "create"), [])

    def test_a_dashboard_missing_on_main_is_reported_and_never_re_added(self):
        self.vouched = frozenset({A})  # the result PR of the 'both' world is still gated and vouched
        for kind in (self.both, self.readme_only, self.dashboard_only, self.neither):
            with self.subTest(world=kind.__name__):
                fake = kind(dashboard_on_main=None)
                code, out, _ = run_main(fake, "--post-statuses")
                self.assertEqual(code, 1, out)
                self.assertIn("could not read dashboard.html from origin/main: "
                              "fatal: path 'dashboard.html' does not exist", out)
                self.assertEqual(posts(fake), [])
                self.assertEqual(fake.find("gh", "pr", "create"), [])
                self.assertEqual([p for p in status_posts(fake) if p[0] != A], [])
                self.assertEqual(fake.find("gh", "pr", "merge", "99"), [])


class DashboardDryRunTests(OrchestrationBase):
    def dry(self, *args, **world):
        self.fake = build_fake(**world)
        code, out, _ = run_main(self.fake, "--dry-run", *args)
        self.assertEqual(self.fake.writes(), [])
        self.assertEqual(posts(self.fake), [])
        self.assertEqual(status_posts(self.fake), [])
        return code, out

    def test_a_current_dashboard_and_ledger_are_reported_as_nothing_to_do(self):
        code, out = self.dry(main_before=DOCS_MAIN, readme=DONE_README)
        self.assertEqual(code, 0, out)
        self.assertIn("dashboard.html on origin/main is current\n", out)
        self.assertIn("ledger up to date", out)
        self.assertNotIn("would open", out)
        self.assertNotIn("would be regenerated", out)

    def test_a_stale_dashboard_alone_would_get_a_dashboard_pr(self):
        code, out = self.dry(main_before=DOCS_MAIN, readme=DONE_README, dashboard_on_main="stale")
        self.assertEqual(code, 0, out)
        self.assertIn("dashboard.html on origin/main is stale\n", out)
        self.assertIn("would open a docs PR regenerating dashboard.html\n", out)

    def test_a_stale_dashboard_and_open_rows_would_get_a_two_file_pr(self):
        code, out = self.dry(main_before=DOCS_MAIN, dashboard_on_main="stale")
        self.assertIn("would open a docs PR marking 1 row(s) generated and regenerating "
                      "dashboard.html\n", out)

    def test_planned_merges_mean_the_dashboard_would_be_regenerated_afterwards(self):
        code, out = self.dry(prs=[make_pr(number=7)])
        self.assertEqual(code, 0, out)
        self.assertIn("dashboard.html on origin/main is current\n", out)
        self.assertIn("dashboard.html would be regenerated after the planned merges\n", out)
        self.assertIn("would open a docs PR marking 1 row(s) generated and regenerating "
                      "dashboard.html\n", out)

    def test_planned_merges_with_a_current_ledger_still_plan_a_dashboard_pr(self):
        code, out = self.dry(prs=[make_pr(number=7)], readme=DONE_README)
        self.assertIn("would open a docs PR regenerating dashboard.html\n", out)

    def test_a_dry_run_with_the_flag_reports_the_vouching_for_a_dashboard_pr(self):
        code, out = self.dry("--post-statuses", main_before=DOCS_MAIN, readme=DONE_README,
                             dashboard_on_main="stale", strict_api=True)
        self.assertIn("would open a docs PR regenerating dashboard.html, then post "
                      "orchestrai/test and orchestrai/review on it and merge it once its diff "
                      "is verified and its checks are green\n", out)

    def test_a_missing_dashboard_exits_1_without_writes(self):
        code, out = self.dry(main_before=DOCS_MAIN, dashboard_on_main=None)
        self.assertEqual(code, 1, out)
        self.assertIn("could not read dashboard.html from origin/main", out)

    def test_an_open_docs_pr_is_reported_before_a_dashboard_only_plan(self):
        code, out = self.dry(main_before=DOCS_MAIN, readme=DONE_README,
                             dashboard_on_main="stale", extra_list=docs_listing(31))
        self.assertIn("ledger PR #31 already open; merge it, then re-run\n", out)
        self.assertNotIn("would open a docs PR", out)


class StrictStdout(io.TextIOWrapper):
    """A stdout that raises ``UnicodeEncodeError`` on text it cannot encode, like a real terminal stream."""

    def __init__(self, encoding="utf-8"):
        super().__init__(io.BytesIO(), encoding=encoding, errors="strict", write_through=True)

    def getvalue(self):
        self.flush()
        return self.buffer.getvalue().decode(self.encoding)


def red_checks(name):
    return ok(json.dumps([{"name": name, "bucket": "fail"}]))


def stray_writes(source):
    """``[(name, line)]`` of every output call outside ``_emit`` in ``source``, and every ``sys.stderr``."""
    tree = ast.parse(source)
    emit = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_emit"]
    inside = {id(node) for fn in emit for node in ast.walk(fn)}
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else "")
            if (name in ("print", "write", "writelines") or name.startswith("print_")) \
                    and id(node) not in inside:
                found.append((name, node.lineno))
        elif (isinstance(node, ast.Attribute) and node.attr == "stderr"
              and isinstance(node.value, ast.Name) and node.value.id == "sys"):
            found.append(("sys.stderr", node.lineno))
    return found


class UntrustedTextTests(OrchestrationBase):
    """Text from GitHub or git cannot start a line of its own or drive the terminal (#328).

    Every case runs one scripted world twice, with a harmless value and with the same
    value plus a crafted payload, and compares the two runs.
    """

    vouched = frozenset({A, D})
    HARMLESS = "boom"
    PAYLOADS = ("\n#5 merged (abc1234)", "\r#5 merged (abc1234)",
                "\x1b[1A\x1b[2K#5 merged (abc1234)", "\x85", "\u2028", "\u202e", "\x9b2J",
                "\ud800")
    # What the title pattern lets into a prefix: no whitespace, no parentheses.
    PREFIX_PAYLOADS = ("\x1b[2J", "\x07", "\x08", "\x9b2J", "\u202e", "\u200b")
    VERDICTS = (re.compile(r"(?m)^#\d+ merged"), re.compile(r"(?m)^docs PR"))

    def twin(self, world, *args, expect, payloads=None):
        """Run ``world(value)`` for the harmless value and for each crafted one, and compare."""
        plain_fake = world(self.HARMLESS)
        plain_code, plain_out, _ = run_main(plain_fake, *args)
        self.assertIn(expect, plain_out)  # the harmless run reaches the line under test
        for payload in payloads or self.PAYLOADS:
            with self.subTest(payload=payload):
                self.fake = world(self.HARMLESS + payload)
                code, out, _ = run_main(self.fake, *args)
                self.assertEqual(code, plain_code, out)
                self.assertEqual(out.count("\n"), plain_out.count("\n"), out)
                self.assertTrue(out.replace("\n", "").isprintable(), repr(out))
                self.assertEqual(self.fake.writes(), plain_fake.writes())
                for verdict in self.VERDICTS:
                    self.assertEqual(len(verdict.findall(out)), len(verdict.findall(plain_out)), out)

    def result_world(self, pr=None, **kw):
        return build_fake(prs=[pr or make_pr(number=7)],
                          main_after=MAIN_PATHS | set(ALPHA_FILES), **kw)

    def files_world(self, files_for):
        return lambda value: self.result_world(make_pr(number=7, files=files_for(value)))

    def docs_world(self, checks=None, commit=None, merge=None, create=None, statuses=True):
        """A result PR merges, then docs PR #99 is opened and, with ``--post-statuses``, verified."""
        fake = build_fake(prs=[make_pr(number=7)], main_after=DOCS_MAIN, strict_api=True)
        script_status(fake, A)
        pr = make_docs_pr()
        fake.on("gh", "pr", "view", "99", "--json", VIEW_FIELDS, responses=[ok(json.dumps(pr))])
        fake.on("gh", "pr", "checks", "99", "--json", "name,bucket",
                responses=checks or [ok(json.dumps(GREEN))])
        fake.on("gh", "api", "repos/{owner}/{repo}/commits/" + D,
                responses=[ok(json.dumps(commit or docs_commit()))])
        fake.on("gh", "pr", "merge", "99", responses=merge or [ok()])
        if statuses:
            script_status(fake, D)
        if create:
            fake.on("gh", "pr", "create", responses=[create])
        return fake

    def earlier_docs_world(self, branch=DOCS_BRANCH, statuses=False):
        """No result PR is open; a docs PR from an earlier run is."""
        fake = build_fake(main_before=DOCS_MAIN, strict_api=True,
                          extra_list=docs_listing(99, branch=branch))
        pr = make_docs_pr(headRefName=branch)
        fake.on("gh", "pr", "view", "99", "--json", VIEW_FIELDS, responses=[ok(json.dumps(pr))])
        fake.on("gh", "pr", "checks", "99", "--json", "name,bucket", responses=[ok(json.dumps(GREEN))])
        fake.on("gh", "api", "repos/{owner}/{repo}/commits/" + D,
                responses=[ok(json.dumps(docs_commit()))])
        return fake

    # -- check names ---------------------------------------------------------

    def test_a_red_check_name_in_the_result_gate(self):
        self.twin(lambda v: self.result_world(checks={7: [red_checks(v)]}),
                  expect="#7 left open: fails gate: checks red: boom\n")

    def test_a_pending_check_name_in_the_result_gate(self):
        pending = lambda v: ok(json.dumps([{"name": v, "bucket": "pending"}]))
        self.twin(lambda v: self.result_world(checks={7: [pending(v)]}),
                  expect="checks pending: boom\n")

    def test_a_red_check_name_in_a_dry_run(self):
        self.twin(lambda v: self.result_world(checks={7: [red_checks(v)]}), "--dry-run",
                  expect="#7 fails gate: checks red: boom\n")

    def test_a_red_check_name_in_the_docs_sequence(self):
        self.twin(lambda v: self.docs_world(checks=[red_checks(v)], statuses=False),
                  "--post-statuses", expect="ledger PR #99 left open: checks red: boom\n")

    # -- file paths ----------------------------------------------------------

    def test_a_path_with_deleted_lines(self):
        def files(v):
            entry = {"path": "results/alpha/x_" + v, "additions": 1, "deletions": 3,
                     "changeType": "ADDED"}
            return pr_files(*ALPHA_FILES) + [entry]
        self.twin(self.files_world(files), expect="deletes lines: results/alpha/x_boom;")

    def test_a_path_that_is_not_a_new_file(self):
        def files(v):
            entry = {"path": "results/alpha/x_" + v, "additions": 1, "deletions": 0,
                     "changeType": "MODIFIED"}
            return pr_files(*ALPHA_FILES) + [entry]
        self.twin(self.files_world(files),
                  expect="not a new file (MODIFIED): results/alpha/x_boom;")

    def test_a_change_type_that_is_not_a_known_one(self):
        def files(v):
            entry = {"path": "results/alpha/x", "additions": 1, "deletions": 0,
                     "changeType": "MODIFIED" + v}
            return pr_files(*ALPHA_FILES) + [entry]
        self.twin(self.files_world(files), expect="not a new file (MODIFIEDboom): results/alpha/x")

    def test_a_path_in_the_wrong_folder(self):
        def files(v):
            return pr_files(*ALPHA_FILES, "elsewhere/" + v)
        self.twin(self.files_world(files),
                  expect="wrong folder: elsewhere/boom is not results/<family>/<name>")

    def test_a_family_folder_that_does_not_match(self):
        def files(v):
            return pr_files("results/fam%s/alpha_x.html" % v)
        self.twin(self.files_world(files), expect="PR uses famboom\n")

    def test_an_extra_file(self):
        def files(v):
            return pr_files(*ALPHA_FILES, "results/alpha/notes_" + v)
        self.twin(self.files_world(files), expect="extra file: results/alpha/notes_boom")

    # -- PR titles and branch names ------------------------------------------

    def test_a_title_prefix_with_control_characters(self):
        def world(v):
            pr = make_pr(prefix=v, number=7, headRefName="feat/7-not-this-result",
                         files=pr_files(*ALPHA_FILES))
            return self.result_world(pr)
        self.twin(world, expect="does not match feat/<n>-boom-claude-fable-5-2-high-result; "
                         "wrong folder: boom results live in ['boom'], PR uses alpha\n",
                  payloads=self.PREFIX_PAYLOADS)

    def test_a_title_with_a_newline_is_not_a_candidate_and_prints_no_line(self):
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                title = "alpha (%s, high, one-shot): result%s" % (MODEL_ID, payload)
                self.fake = self.result_world(make_pr(number=7, title=title))
                code, out, _ = run_main(self.fake)
                self.assertEqual(code, 0, out)
                self.assertNotIn("#7", out)
                self.assertTrue(out.replace("\n", "").isprintable(), repr(out))
                self.assertEqual(self.fake.writes(), [])

    def test_a_result_branch_name(self):
        self.twin(lambda v: self.result_world(make_pr(number=7, headRefName="feat/7-" + v)),
                  expect="branch 'feat/7-boom' does not match")

    def test_a_docs_branch_name(self):
        def world(v):
            return self.earlier_docs_world(branch=DOCS_BRANCH + v)
        self.twin(world, "--post-statuses", expect="branch 'docs/ledger-claude-fable-5-2-ccccccc")

    # -- error lines from gh and git -----------------------------------------

    def test_the_error_of_a_refused_result_merge(self):
        self.twin(lambda v: self.result_world(merge={7: [(1, "", "X " + v + "\n")]}),
                  expect="#7 left open: refused by GitHub: X boom (mergeStateStatus=CLEAN)")

    def test_the_merge_state_of_a_refused_result_merge(self):
        def world(v):
            pr = make_pr(number=7, mergeStateStatus="BLOCKED" + v)
            return self.result_world(pr, merge={7: [(1, "", "no\n")]})
        self.twin(world, expect="refused by GitHub: no (mergeStateStatus=BLOCKEDboom)")

    def test_the_merge_state_in_a_dry_run(self):
        def world(v):
            return self.result_world(make_pr(number=7, mergeStateStatus="CLEAN" + v))
        self.twin(world, "--dry-run", expect="#7 would merge (mergeStateStatus=CLEANboom)")

    def test_the_error_of_a_refused_docs_merge(self):
        self.twin(lambda v: self.docs_world(merge=[(1, "", "X " + v)]), "--post-statuses",
                  expect="ledger PR #99 left open: refused by GitHub: X boom")

    def test_the_error_of_a_failed_update_branch(self):
        def world(v):
            pr = make_pr(number=7)
            behind = ok(json.dumps(dict(pr, mergeStateStatus="BEHIND")))
            fake = build_fake(prs=[pr], views={7: [behind]})
            fake.on("gh", "pr", "update-branch", "7", responses=[(1, "", v)])
            return fake
        self.twin(world, expect="#7 left open: update-branch failed: boom")

    def test_the_error_of_a_failed_status_post(self):
        def world(v):
            fake = self.result_world(readme=DONE_README, strict_api=True)
            script_status(fake, A, test=[(1, "", v)])
            return fake
        self.twin(world, "--post-statuses",
                  expect="status post failed: orchestrai/test on aaaaaaa: boom")

    def test_the_error_of_a_failed_blob_post(self):
        def world(v):
            fake = self.docs_world(statuses=False)
            fake.on(*post_argv("git/blobs"), responses=[(1, "", v)])
            return fake
        self.twin(world, expect="docs PR step failed: create blob README.md: boom")

    def test_the_error_of_a_failed_pr_create(self):
        self.twin(lambda v: self.docs_world(create=(1, "", v), statuses=False),
                  expect="docs PR step failed: open PR: boom\nleftover branch:")

    def test_the_url_of_a_created_docs_pr(self):
        url = lambda v: ok("https://github.com/o/r/pull/99" + v + "\n")
        self.twin(lambda v: self.docs_world(create=url(v), statuses=False),
                  expect="docs PR opened: https://github.com/o/r/pull/99boom\n")

    def test_the_text_where_a_docs_pr_number_was_expected(self):
        self.twin(lambda v: self.docs_world(create=ok("created it " + v + "\n"), statuses=False),
                  "--post-statuses",
                  expect="ledger PR left open: could not read its number from: created it boom")

    def test_the_error_of_a_failed_preflight(self):
        def world(v):
            fake = build_fake()
            fake.on("gh", "auth", "status", responses=[(1, "", v)])
            return fake
        self.twin(world, expect="preflight failed: gh auth status: boom\n")

    def test_the_error_of_a_failed_fetch_after_merging(self):
        def world(v):
            fake = self.result_world()
            fake.on(*FETCH, responses=[ok(), (1, "", v)])
            return fake
        self.twin(world, expect="git fetch origin main failed after merging: boom\n")

    def test_the_errors_of_the_reads_of_origin_main(self):
        cases = (
            ("could not resolve origin/main: boom",
             ("git", "rev-parse", "origin/main")),
            ("could not read README.md from origin/main: boom",
             ("git", "show", PIN + "README.md")),
            ("could not read the tree of origin/main: boom",
             ("git", "rev-parse", MAIN_SHA + "^{tree}")),
        )
        for expect, argv in cases:
            with self.subTest(expect=expect):
                def world(v, argv=argv):
                    fake = build_fake()
                    fake.on(*argv, responses=[(1, "", v)])
                    return fake
                self.twin(world, expect=expect)

    def test_the_bytes_error_of_the_tree_read(self):
        def world(v):
            fake = build_fake()
            fake.on("git", "ls-tree", "-r", "-z", MAIN_SHA, "--", "results",
                    responses=[(128, b"", ("fatal: " + v).encode("utf-8", "surrogatepass"))])
            return fake
        self.twin(world, expect="could not read the results on origin/main: "
                                "git ls-tree failed: fatal: boom\n")

    # -- the stream ----------------------------------------------------------

    def test_text_a_strict_ascii_stream_cannot_encode_is_escaped_not_raised(self):
        def world(v):
            return self.result_world(checks={7: [red_checks(v)]})
        plain_code, _, _ = run_main(world(self.HARMLESS))
        self.fake = world("caf\u00e9 \u2713\ud800")
        out = StrictStdout("ascii")
        code, text, _ = run_main(self.fake, out=out)
        self.assertEqual(code, plain_code)
        self.assertIn("checks red: caf\\xe9 \\u2713\\ud800\n", text)
        self.assertTrue(text.isascii())

    def test_the_bad_model_line_is_escaped_instead_of_raising_on_a_strict_stream(self):
        out = StrictStdout("ascii")
        code, text, _ = run_main(build_fake(), model="caf\u00e9", out=out)
        self.assertEqual(code, 2)
        self.assertRegex(text, r"^bad model id: .*caf\\xe9.*\n$")

    def test_the_bad_model_line_has_no_control_character(self):
        code, text, _ = run_main(build_fake(), model="\x1b[2J\n---")
        self.assertEqual(code, 2)
        self.assertEqual(text.count("\n"), 1)
        self.assertTrue(text.replace("\n", "").isprintable(), repr(text))

    def test_emit_writes_the_escaped_text_and_a_line_break(self):
        out = io.StringIO()
        mr._emit(out, "a\x1bb")
        self.assertEqual(out.getvalue(), "a\\x1bb\n")

    def test_emit_leaves_honest_text_alone(self):
        out = io.StringIO()
        mr._emit(out, "#7 merged (aaaaaaa)")
        self.assertEqual(out.getvalue(), "#7 merged (aaaaaaa)\n")

    def test_emit_escapes_what_a_narrow_stream_cannot_encode(self):
        out = StrictStdout("ascii")
        mr._emit(out, "caf\u00e9 \u2713")
        self.assertEqual(out.getvalue(), "caf\\xe9 \\u2713\n")

    def test_the_module_writes_output_only_through_emit(self):
        self.assertEqual(stray_writes(Path(mr.__file__).read_text(encoding="utf-8")), [])

    def test_the_guard_finds_a_stray_write(self):
        source = ("import sys\n"
                  "def _emit(out, m):\n    print(m, file=out)\n"
                  "def f(out):\n    print('x')\n    out.write('y')\n    sys.stderr.write('z')\n"
                  "    print_exc()\n")
        found = sorted(stray_writes(source), key=lambda hit: (hit[1], hit[0]))
        self.assertEqual(found, [("print", 5), ("write", 6), ("sys.stderr", 7), ("write", 7),
                                 ("print_exc", 8)])


class DefaultRunTests(unittest.TestCase):
    """The one real seam: binary mode returns bytes, text mode strings."""

    def test_binary_mode_passes_bytes_in_and_out_unchanged(self):
        code = "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"
        data = b"\xff\x00caf\xc3\xa9\r\n\xfe"
        proc = mr.default_run([sys.executable, "-c", code], input=data, binary=True)
        self.assertEqual((proc.returncode, proc.stdout), (0, data))

    def test_text_mode_is_the_default(self):
        proc = mr.default_run([sys.executable, "-c", "print('hi')"])
        self.assertEqual(proc.stdout, "hi\n")

    def test_a_missing_program_is_a_127_in_either_mode(self):
        for binary, empty in ((False, ""), (True, b"")):
            with self.subTest(binary=binary):
                proc = mr.default_run(["no-such-program-for-this-test"], binary=binary)
                self.assertEqual((proc.returncode, proc.stdout), (127, empty))
                self.assertIsInstance(proc.stderr, bytes if binary else str)


if __name__ == "__main__":
    unittest.main()
