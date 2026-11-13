"""Unit tests for ``merge_results.py``: gate, ledger rewrite, orchestration.

Nothing here touches the network or the real repo state: every git and gh
call goes through the ``run`` seam, which the tests replace with a scripted
``FakeRunner``. Prompt TOMLs and PR payloads are inline fixtures.
"""

import base64
import io
import json
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
    return [{"path": p, "additions": 5, "deletions": 0, "changeType": "ADDED"}
            for p in paths]


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
README_BLOB = "d" * 40


def ok(stdout=""):
    return (0, stdout, "")


class FakeRunner:
    """Scripted ``run`` seam: longest argv-prefix match (latest rule wins ties)."""

    def __init__(self):
        self.rules = []
        self.calls = []

    def on(self, *prefix, responses):
        self.rules.append((prefix, list(responses)))

    def __call__(self, argv, input=None):
        argv = tuple(argv)
        self.calls.append((argv, input))
        best = None
        for prefix, queue in self.rules:
            if argv[:len(prefix)] == prefix and (best is None or len(prefix) >= len(best[0])):
                best = (prefix, queue)
        if best is None:
            raise AssertionError("unscripted call: %r" % (argv,))
        queue = best[1]
        rc, stdout, stderr = queue.pop(0) if len(queue) > 1 else queue[0]
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


def build_fake(prs=(), main_before=MAIN_PATHS, main_after=None, readme=README,
               views=None, checks=None, extra_list=(), merge=None):
    """Script a world: ``prs`` are open; ``views``/``checks``/``merge`` override per PR."""
    fake = FakeRunner()
    views, checks, merge = views or {}, checks or {}, merge or {}
    fake.on("gh", "auth", "status", responses=[ok()])
    fake.on(*FETCH, responses=[ok()])
    fake.on(*LIST_ARGV, responses=[listing(prs, extra_list)])
    after = main_before if main_after is None else main_after
    fake.on(*LS_TREE, responses=[tree(main_before), tree(after)])
    fake.on("git", "show", "origin/main:README.md", responses=[ok(readme)])
    fake.on("git", "rev-parse", "origin/main:README.md", responses=[ok(README_BLOB + "\n")])
    fake.on("git", "rev-parse", "origin/main", responses=[ok(MAIN_SHA + "\n")])
    for pr in prs:
        n = str(pr["number"])
        fake.on("gh", "pr", "view", n, "--json", VIEW_FIELDS,
                responses=views.get(pr["number"], [ok(json.dumps(pr))]))
        fake.on("gh", "pr", "checks", n, "--json", "name,bucket",
                responses=checks.get(pr["number"], [ok(json.dumps(GREEN))]))
        fake.on("gh", "pr", "merge", n, responses=merge.get(pr["number"], [ok()]))
        fake.on("gh", "pr", "update-branch", n, responses=[ok()])
    fake.on("gh", "api", "--method", "POST", responses=[ok("{}")])
    fake.on("gh", "api", "--method", "PUT", responses=[ok("{}")])
    fake.on("gh", "pr", "create", responses=[ok("https://github.com/o/r/pull/99\n")])
    return fake


def run_main(fake, *args, model=MODEL_ID):
    sleeps = []
    out = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in (("game-alpha.toml", ALPHA_TOML), ("app-beta.toml", BETA_TOML)):
            Path(tmp, name).write_text(text, encoding="utf-8")
        code = mr.main(["--model=" + model, *args], run=fake, sleep=sleeps.append,
                       prompts_dir=tmp, out=out)
    return code, out.getvalue(), sleeps


class OrchestrationBase(unittest.TestCase):
    fake = None

    def tearDown(self):
        if self.fake is not None:
            for argv in self.fake.argvs():
                self.assertNotIn("--admin", argv)
                self.assertNotIn("--auto", argv)
                self.assertNotIn("--delete-branch", argv)


ALPHA_FILES = ["results/alpha/alpha_%s.html" % TAG, "results/alpha/alpha_%s.meta.json" % TAG]
BETA_FILES = ["results/beta/beta_%s.md" % TAG, "results/beta/beta_%s.meta.json" % TAG]


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
             ("git", "show", "origin/main:README.md")})

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
        self.fake = build_fake(prs=[pr], main_after=MAIN_PATHS | set(ALPHA_FILES))
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0, out)
        merge_call = self.fake.find("gh", "pr", "merge")
        self.assertEqual(len(merge_call), 1)
        self.assertEqual(merge_call[0][0], (
            "gh", "pr", "merge", "7", "--squash", "--match-head-commit", "a" * 40,
            "--subject", "feat(results): add alpha %s one-shot result (#7)" % MODEL_ID))
        branch = "docs/ledger-claude-fable-5-2-" + MAIN_SHA[:7]
        ref_call = self.fake.find("gh", "api", "--method", "POST")
        self.assertIn("repos/{owner}/{repo}/git/refs", ref_call[0][0])
        self.assertEqual(json.loads(ref_call[0][1]),
                         {"ref": "refs/heads/" + branch, "sha": MAIN_SHA})
        put_call = self.fake.find("gh", "api", "--method", "PUT")
        self.assertIn("repos/{owner}/{repo}/contents/README.md", put_call[0][0])
        body = json.loads(put_call[0][1])
        self.assertEqual(body["branch"], branch)
        self.assertEqual(body["sha"], README_BLOB)
        new_readme = base64.b64decode(body["content"]).decode("utf-8")
        self.assertEqual(
            status_cell(new_readme, "results/alpha/alpha_claude_fable_5_2.html"),
            "generated, browser check pending")
        self.assertEqual(
            status_cell(new_readme, "results/beta/beta_claude_fable_5_2.md"), "not run")
        create = self.fake.find("gh", "pr", "create")[0][0]
        self.assertEqual(create[create.index("--head") + 1], branch)
        self.assertEqual(create[create.index("--base") + 1], "main")
        self.assertEqual(create[create.index("--title") + 1],
                         "docs(readme): mark 1 claude-fable-5-2 ledger rows generated")
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
        done = README.replace("alpha_claude_fable_5_2.html` | not run",
                              "alpha_claude_fable_5_2.html` | generated, browser check pending")
        self.fake = build_fake(main_before=MAIN_PATHS | set(ALPHA_FILES), readme=done)
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0)
        self.assertIn("nothing to merge; ledger up to date", out)
        self.assertEqual(self.fake.writes(), [])

    def test_sidecar_missing_is_reported_and_no_pr_opened(self):
        self.fake = build_fake(main_before=MAIN_PATHS | {ALPHA_FILES[0]})
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 0)
        self.assertIn("left as not run: sidecar missing", out)
        self.assertEqual(self.fake.writes(), [])

    def test_ref_creation_failure_exits_1_naming_the_step(self):
        self.fake = build_fake(main_before=MAIN_PATHS | set(ALPHA_FILES))
        self.fake.on("gh", "api", "--method", "POST", responses=[(1, "", "HTTP 422\n")])
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 1)
        self.assertIn("docs PR step failed: create branch: HTTP 422", out)
        self.assertEqual(self.fake.find("gh", "pr", "create"), [])

    def test_commit_failure_names_the_leftover_branch(self):
        self.fake = build_fake(main_before=MAIN_PATHS | set(ALPHA_FILES))
        self.fake.on("gh", "api", "--method", "PUT", responses=[(1, "", "HTTP 409\n")])
        code, out, _ = run_main(self.fake)
        self.assertEqual(code, 1)
        self.assertIn("docs PR step failed: update README: HTTP 409", out)
        self.assertIn("leftover branch: docs/ledger-claude-fable-5-2-" + MAIN_SHA[:7], out)
        self.assertEqual(self.fake.find("gh", "pr", "create"), [])

    def test_docs_pr_is_never_merged(self):
        self.fake = build_fake(main_before=MAIN_PATHS | set(ALPHA_FILES))
        code, _, _ = run_main(self.fake)
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.find("gh", "pr", "merge"), [])


if __name__ == "__main__":
    unittest.main()
