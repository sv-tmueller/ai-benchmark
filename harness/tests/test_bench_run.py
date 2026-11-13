"""Unit tests for ``bench_run.py``, the single-prompt partner of ``bench_run_all.py``.

``git`` and ``gh`` go through the module's single ``_run`` seam, which the
tests replace; ``grade.py`` is replaced by a fake script. Nothing here starts
a model or touches the network.
"""

import contextlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from harness import bench_run as br
from harness import bench_run_all as bra
from harness import merge_results

REPO = Path(__file__).resolve().parents[2]

GAME = """\
id = "game-x"
title = "Game X"
category = "game-generation"
file_prefix = "gx"
save_as = "html"
temperature = 0.7
max_tokens = 4096

[system]
text = "SYS-TEXT"

[user]
text = "USER-TEXT line one\\nline two"
"""

APP = """\
id = "app-y"
title = "App Y"
category = "app-generation"
file_prefix = "ay"
save_as = "md"

[user]
text = "build app y"
"""

GRADED = """\
id = "math-z"
title = "Math Z"
category = "math"
file_prefix = "mz"
save_as = "txt"

[user]
text = "what is 2+2"

[images]
files = ["assets/a.png"]

[grading]
mode = "contains"
"""

PARAM = """\
id = "param-p"
title = "Param P"
file_prefix = "pp"
save_as = "txt"

[user]
text = "x"
"""


def meta_for(pid, deliverable):
    return json.dumps({"prompt_id": pid, "outputs": {"deliverable": deliverable}})


class Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


class RepoCase(unittest.TestCase):
    """A temp repo root with three prompts, one prior result each, and a fake git/gh seam."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        prompts = self.root / "prompts"
        prompts.mkdir()
        (prompts / "game-x.toml").write_text(GAME)
        (prompts / "app-y.toml").write_text(APP)
        (prompts / "math-z.toml").write_text(GRADED)
        (prompts / "param-p.toml").write_text(PARAM)
        (prompts / "param-p.fixtures.toml").write_text("[[cases]]\n")
        for folder, pid, name in (("gx-dir", "game-x", "gx_claude_opus_5_5.html"),
                                  ("ay-dir", "app-y", "ay_claude_opus_5_5.md"),
                                  ("mz-dir", "math-z", "mz_claude_opus_5_5.txt")):
            d = self.root / "results" / folder
            d.mkdir(parents=True)
            stem = name.rsplit(".", 1)[0]
            (d / (stem + ".meta.json")).write_text(
                meta_for(pid, "results/%s/%s" % (folder, name)))
        self.main_paths = set()
        self.open_prs = []
        self.gh_fails = False
        self.calls = []
        self.env = {"CLAUDE_EFFORT": "high"}

    def fake_run(self, cmd, cwd=None):
        self.calls.append(list(cmd))
        if cmd[:2] == ["git", "cat-file"]:
            path = cmd[3].split(":", 1)[1]
            return Proc(0 if path in self.main_paths else 1)
        if cmd[:3] == ["gh", "pr", "list"]:
            if self.gh_fails:
                return Proc(1, "", "boom")
            return Proc(0, json.dumps(self.open_prs))
        raise AssertionError("unexpected command %r" % (cmd,))

    def invoke(self, *argv, environ=None, grade_script=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = br.main(list(argv), environ=self.env if environ is None else environ,
                           repo_root=self.root, run=self.fake_run, grade_script=grade_script)
        return code, out.getvalue(), err.getvalue()

    def write_deliverable(self, rel="results/gx-dir/gx_claude_fable_5_2.html", text="<!DOCTYPE html>x"):
        path = self.root / rel
        path.write_text(text)
        return path


class PlanTest(RepoCase):
    def test_plan_prints_key_lines_and_a_meta_preview(self):
        code, out, _ = self.invoke("plan", "game-x", "claude-fable-5-2")
        self.assertEqual(code, 0)
        for line in ("prompt_id: game-x", "toml: game-x.toml", "folder: results/gx-dir",
                     "prefix: gx", "extension: html", "kind: single HTML file",
                     "model_tag: claude_fable_5_2 (harness derive_model agrees)",
                     "target: results/gx-dir/gx_claude_fable_5_2.html",
                     "meta: results/gx-dir/gx_claude_fable_5_2.meta.json",
                     "grading_sidecar: results/gx-dir/gx_claude_fable_5_2_grading.json",
                     "grading_mode: none", "grade_command: none (no [grading] rule)",
                     "issue_title: game-x: claude-fable-5-2 one-shot result",
                     "branch: feat/<N>-gx-claude-fable-5-2-result",
                     "commit: feat(results): add gx claude-fable-5-2 one-shot result (#<N>)",
                     "pr_title: gx (claude-fable-5-2, one-shot): result", "meta_preview:"):
            self.assertIn(line + "\n", out)
        preview = json.loads(out.split("meta_preview:\n", 1)[1])
        self.assertEqual(preview["model"], "claude-fable-5-2")
        self.assertEqual(preview["params"]["reasoning_effort"], "high")
        self.assertEqual(preview["generated_utc"], "<UTC timestamp stamped in meta mode>")

    def test_plan_writes_nothing_and_reads_no_result_content(self):
        before = sorted(str(p) for p in self.root.rglob("*"))
        self.invoke("plan", "game-x", "claude-fable-5-2")
        self.assertEqual(sorted(str(p) for p in self.root.rglob("*")), before)

    def test_blueprint_kind_for_md_app_prompts_and_text_for_the_rest(self):
        _, out, _ = self.invoke("plan", "app-y", "claude-fable-5-2")
        self.assertIn("kind: single markdown blueprint\n", out)
        _, out, _ = self.invoke("plan", "math-z", "claude-fable-5-2")
        self.assertIn("kind: text answer\n", out)

    def test_reasoning_effort_is_null_when_the_variable_is_unset(self):
        _, out, _ = self.invoke("plan", "game-x", "claude-fable-5-2", environ={})
        self.assertIsNone(json.loads(out.split("meta_preview:\n", 1)[1])["params"]["reasoning_effort"])

    def test_graded_prompt_shows_the_new_grade_command(self):
        _, out, _ = self.invoke("plan", "math-z", "claude-fable-5-2")
        self.assertIn("grading_mode: contains\n", out)
        self.assertIn("grade_command: python3 harness/bench_run.py grade math-z claude-fable-5-2\n", out)

    def test_stem_lookup_and_context_suffix_strip(self):
        code, out, _ = self.invoke("plan", "game-x", "claude-fable-5-2[1m]")
        self.assertEqual(code, 0)
        self.assertIn("issue_title: game-x: claude-fable-5-2 one-shot result\n", out)

    def assert_stop(self, argv, fragment):
        code, out, _ = self.invoke(*argv)
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP: "), out)
        self.assertIn(fragment, out)
        self.assertEqual(out.count("\n"), 1)

    def test_stops_on_unknown_prompt(self):
        self.assert_stop(("plan", "nope", "claude-fable-5-2"), "0 prompts match")

    def test_stops_on_parametrized_prompt(self):
        self.assert_stop(("plan", "param-p", "claude-fable-5-2"), "parametrized")

    def test_stops_on_wrong_argument_count_or_mode(self):
        self.assert_stop(("plan", "game-x"), "usage")
        self.assert_stop(("bogus", "game-x", "claude-fable-5-2"), "usage")

    def test_stops_when_results_folder_is_ambiguous(self):
        d = self.root / "results" / "gx-other"
        d.mkdir()
        (d / "gx_claude_haiku_5_5.meta.json").write_text(
            meta_for("game-x", "results/gx-other/gx_claude_haiku_5_5.html"))
        self.assert_stop(("plan", "game-x", "claude-fable-5-2"), "2 results folders")

    def test_stops_when_target_exists_on_disk(self):
        self.write_deliverable()
        self.assert_stop(("plan", "game-x", "claude-fable-5-2"), "already exists on disk")

    def test_stops_when_target_is_on_origin_main(self):
        self.main_paths.add("results/gx-dir/gx_claude_fable_5_2.html")
        self.assert_stop(("plan", "game-x", "claude-fable-5-2"), "already exists at origin/main")

    def test_stops_when_an_open_pr_touches_the_target(self):
        self.open_prs = [{"number": 7, "files": [{"path": "results/gx-dir/gx_claude_fable_5_2.html"}]}]
        self.assert_stop(("plan", "game-x", "claude-fable-5-2"), "open PR #7")

    def test_stops_when_gh_fails(self):
        self.gh_fails = True
        self.assert_stop(("plan", "game-x", "claude-fable-5-2"), "gh pr list failed")

    def test_stops_on_an_unusable_model_tag(self):
        self.assert_stop(("plan", "game-x", "---"), "model tag")

    def test_other_models_results_do_not_block(self):
        code, _, _ = self.invoke("plan", "game-x", "claude-opus-5-6")
        self.assertEqual(code, 0)


class MetaTest(RepoCase):
    def test_meta_requires_the_deliverable_and_writes_nothing_without_it(self):
        code, out, _ = self.invoke("meta", "game-x", "claude-fable-5-2")
        self.assertEqual(code, 1)
        self.assertIn("STOP: results/gx-dir/gx_claude_fable_5_2.html is missing or empty", out)
        self.assertFalse((self.root / "results/gx-dir/gx_claude_fable_5_2.meta.json").exists())

    def test_meta_rejects_an_empty_deliverable(self):
        self.write_deliverable(text="")
        code, out, _ = self.invoke("meta", "game-x", "claude-fable-5-2")
        self.assertEqual(code, 1)
        self.assertIn("missing or empty", out)

    def test_meta_writes_the_sidecar_with_a_stamp_and_the_effort(self):
        self.write_deliverable()
        code, out, _ = self.invoke("meta", "game-x", "claude-fable-5-2")
        self.assertEqual(code, 0)
        self.assertIn("written: results/gx-dir/gx_claude_fable_5_2.meta.json\n", out)
        meta = json.loads((self.root / "results/gx-dir/gx_claude_fable_5_2.meta.json").read_text())
        self.assertRegex(meta["generated_utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(meta["model"], "claude-fable-5-2")
        self.assertEqual(meta["prompt_id"], "game-x")
        self.assertEqual(meta["toml"], "game-x.toml")
        self.assertTrue(meta["one_shot"])
        self.assertEqual(meta["params"]["reasoning_effort"], "high")
        self.assertEqual(meta["outputs"], {"deliverable": "results/gx-dir/gx_claude_fable_5_2.html"})
        self.assertNotIn("playability", json.dumps(meta))

    def test_meta_note_names_the_toml_sampling_values_and_the_system_context(self):
        self.write_deliverable()
        self.invoke("meta", "game-x", "claude-fable-5-2")
        meta = json.loads((self.root / "results/gx-dir/gx_claude_fable_5_2.meta.json").read_text())
        note = meta["params"]["note"]
        self.assertIn("temperature 0.7", note)
        self.assertIn("max_tokens 4096", note)
        self.assertIn("alongside the TOML system text", note)
        self.write_deliverable("results/ay-dir/ay_claude_fable_5_2.md")
        self.invoke("meta", "app-y", "claude-fable-5-2")
        meta = json.loads((self.root / "results/ay-dir/ay_claude_fable_5_2.meta.json").read_text())
        self.assertIn("temperature not set in the TOML", meta["params"]["note"])
        self.assertIn("The TOML has no system text", meta["params"]["note"])

    def test_meta_stops_when_the_meta_already_exists(self):
        self.write_deliverable()
        self.invoke("meta", "game-x", "claude-fable-5-2")
        code, out, _ = self.invoke("meta", "game-x", "claude-fable-5-2")
        self.assertEqual(code, 1)
        self.assertIn("already exists on disk", out)


class PromptTest(RepoCase):
    def test_prompt_prints_system_separator_user_and_image_lines(self):
        code, out, _ = self.invoke("prompt", "game-x", "claude-fable-5-2")
        self.assertEqual(code, 0)
        self.assertEqual(out, "SYS-TEXT\n-----\nUSER-TEXT line one\nline two\n")
        _, out, _ = self.invoke("prompt", "math-z", "claude-fable-5-2")
        self.assertEqual(out, "\n-----\nwhat is 2+2\nimage: prompts/assets/a.png\n")

    def test_prompt_stops_on_an_unknown_id_and_prints_no_prompt_text(self):
        code, out, _ = self.invoke("prompt", "no-such-prompt", "claude-fable-5-2")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP: "))
        self.assertNotIn("-----", out)

    def test_prompt_makes_no_git_or_gh_call_and_reads_no_results(self):
        self.invoke("prompt", "game-x", "claude-fable-5-2")
        self.assertEqual(self.calls, [])

    def test_output_is_byte_identical_to_the_old_one_liner_for_every_real_prompt(self):
        old = ("import tomllib,sys; d=tomllib.load(open(sys.argv[1],'rb')); "
               "print(d.get('system',{}).get('text','')); print('-----'); "
               "print(d['user']['text']); "
               "[print('image: prompts/'+f) for f in d.get('images',{}).get('files',[])]")
        tomls = [p for p in sorted((REPO / "prompts").glob("*.toml"))
                 if not p.name.endswith(".fixtures.toml")
                 and not (REPO / "prompts" / (p.stem + ".fixtures.toml")).exists()]
        self.assertGreater(len(tomls), 20)
        for path in tomls:
            with self.subTest(prompt=path.name):
                pid = tomllib.loads(path.read_text(encoding="utf-8"))["id"]
                want = subprocess.run([sys.executable, "-X", "utf8", "-c", old, str(path)],
                                      capture_output=True, check=True).stdout
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = br.main(["prompt", pid, "claude-fable-5-2"], environ={},
                                   repo_root=REPO, run=self.fake_run)
                self.assertEqual(code, 0)
                self.assertEqual(out.getvalue().encode("utf-8"), want)


class IssueBodyTest(RepoCase):
    def test_issue_body_is_written_under_bench_run_and_its_path_printed(self):
        code, out, _ = self.invoke("issue-body", "game-x", "claude-fable-5-2")
        self.assertEqual(code, 0)
        self.assertEqual(out, ".bench-run/gx_claude_fable_5_2.issue.md\n")
        text = (self.root / ".bench-run/gx_claude_fable_5_2.issue.md").read_text()
        self.assertIn("prompts/game-x.toml", text)
        self.assertIn("plain one-shot", text)
        self.assertIn("/bench-run", text)
        self.assertIn("no orchestrator or agents", text)
        self.assertIn("results/gx-dir/gx_claude_fable_5_2.html", text)
        self.assertIn("results/gx-dir/gx_claude_fable_5_2.meta.json", text)
        self.assertIn("single HTML file", text)
        self.assertNotIn("Closes", text)

    def test_issue_body_lists_the_grading_sidecar_only_for_graded_prompts(self):
        self.invoke("issue-body", "math-z", "claude-fable-5-2")
        graded = (self.root / ".bench-run/mz_claude_fable_5_2.issue.md").read_text()
        self.assertIn("results/mz-dir/mz_claude_fable_5_2_grading.json", graded)
        self.invoke("issue-body", "game-x", "claude-fable-5-2")
        plain = (self.root / ".bench-run/gx_claude_fable_5_2.issue.md").read_text()
        self.assertNotIn("_grading.json", plain)

    def test_issue_body_works_after_the_deliverable_and_meta_exist(self):
        self.write_deliverable()
        self.invoke("meta", "game-x", "claude-fable-5-2")
        code, out, _ = self.invoke("issue-body", "game-x", "claude-fable-5-2")
        self.assertEqual(code, 0, out)

    def test_issue_body_needs_no_git_or_gh(self):
        self.invoke("issue-body", "game-x", "claude-fable-5-2")
        self.assertEqual(self.calls, [])

    def test_issue_body_stops_on_an_unknown_prompt(self):
        code, out, _ = self.invoke("issue-body", "nope", "claude-fable-5-2")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP: "))


class PrBodyTest(RepoCase):
    FOOTER = "\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)"

    def body(self, pid="game-x", prefix="gx", n="12", *extra):
        code, out, err = self.invoke("pr-body", pid, "claude-fable-5-2", n, *extra)
        self.assertEqual(code, 0, out + err)
        path = self.root / out.strip()
        self.assertEqual(out.strip(), ".bench-run/%s_claude_fable_5_2.pr.md" % prefix)
        return path.read_text(encoding="utf-8")

    def test_ungraded_body_has_the_sections_the_naming_section_requires(self):
        text = self.body()
        self.assertIn("one-shot", text)
        self.assertIn("results/gx-dir/gx_claude_fable_5_2.html", text)
        self.assertIn("results/gx-dir/gx_claude_fable_5_2.meta.json", text)
        self.assertIn("no [grading] rule; no playability verdict written; browser verification pending", text)
        self.assertIn("temperature", text)
        self.assertIn("max_tokens", text)
        self.assertIn("usage", text)
        self.assertNotIn("_grading.json", text)

    def test_body_closes_the_issue_and_the_closing_line_stays_in_the_body(self):
        text = self.body(n="12")
        self.assertIn("Closes #12", text)
        self.assertNotIn("Closes #11", text)

    def test_footer_is_the_last_line_and_absent_when_not_given(self):
        text = self.body("game-x", "gx", "12", "--footer", self.FOOTER)
        self.assertEqual(text.rstrip("\n").splitlines()[-1], self.FOOTER)
        self.assertLess(text.index("Closes #12"), text.index(self.FOOTER))
        self.assertNotIn("Generated with", self.body(n="13"))

    def test_graded_body_embeds_the_saved_grade_output_and_lists_the_sidecar(self):
        bench = self.root / ".bench-run"
        bench.mkdir()
        (bench / "mz_claude_fable_5_2.grade.txt").write_text("  PASS  contains  x\ngraded 1 result(s)\n")
        text = self.body("math-z", "mz")
        self.assertIn("  PASS  contains  x", text)
        self.assertIn("graded 1 result(s)", text)
        self.assertIn("results/mz-dir/mz_claude_fable_5_2_grading.json", text)
        self.assertNotIn("no [grading] rule", text)

    def test_graded_body_stops_when_grade_output_is_missing(self):
        code, out, _ = self.invoke("pr-body", "math-z", "claude-fable-5-2", "12")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP: "))
        self.assertIn("grade", out)
        self.assertFalse((self.root / ".bench-run/mz_claude_fable_5_2.pr.md").exists())

    def test_graded_body_stops_when_grade_output_is_empty(self):
        bench = self.root / ".bench-run"
        bench.mkdir()
        (bench / "mz_claude_fable_5_2.grade.txt").write_text("")
        code, out, _ = self.invoke("pr-body", "math-z", "claude-fable-5-2", "12")
        self.assertEqual(code, 1)

    def test_stops_on_a_bad_issue_number_or_dangling_footer_flag(self):
        for argv in (("pr-body", "game-x", "claude-fable-5-2"),
                     ("pr-body", "game-x", "claude-fable-5-2", "abc"),
                     ("pr-body", "game-x", "claude-fable-5-2", "0"),
                     ("pr-body", "game-x", "claude-fable-5-2", "12", "--footer"),
                     ("pr-body", "game-x", "claude-fable-5-2", "12", "--bogus", "x"),
                     ("issue-body", "game-x", "claude-fable-5-2", "12")):
            with self.subTest(argv=argv):
                code, out, _ = self.invoke(*argv)
                self.assertEqual(code, 1)
                self.assertTrue(out.startswith("STOP: usage"), out)


class FakeGradeCase(RepoCase):
    def make_grade(self, exit_code, stdout="  PASS  contains  x\n", stderr="", touch=()):
        """A fake grade.py: writes this run's sidecar (and any other listed ones), then exits."""
        script = self.root / "fake_grade.py"
        script.write_text(
            "import sys\n"
            "sys.stdout.write(%r)\nsys.stderr.write(%r)\n"
            "for p in %r:\n    open(p, 'w').write('{}')\n"
            "assert sys.argv[1:] == ['--prompt', 'math-z'], sys.argv\n"
            "sys.exit(%d)\n" % (stdout, stderr, list(touch), exit_code))
        return script

    OWN = "results/mz-dir/mz_claude_fable_5_2_grading.json"
    OTHER = "results/mz-dir/mz_claude_opus_5_5_grading.json"


class GradeModeTest(FakeGradeCase):
    def test_success_prints_the_output_saves_it_and_keeps_the_sidecars(self):
        script = self.make_grade(0, touch=(str(self.root / self.OWN),))
        code, out, _ = self.invoke("grade", "math-z", "claude-fable-5-2", grade_script=script)
        self.assertEqual(code, 0)
        self.assertEqual(out, "  PASS  contains  x\n")
        self.assertEqual((self.root / ".bench-run/mz_claude_fable_5_2.grade.txt").read_text(),
                         "  PASS  contains  x\n")
        self.assertTrue((self.root / self.OWN).exists())

    def test_failure_removes_only_this_runs_own_sidecar(self):
        script = self.make_grade(1, stdout="  ERR boom\n", stderr="sympy missing\n",
                                 touch=(str(self.root / self.OWN), str(self.root / self.OTHER)))
        code, out, err = self.invoke("grade", "math-z", "claude-fable-5-2", grade_script=script)
        self.assertEqual(code, 1)
        self.assertIn("  ERR boom", out)
        self.assertIn("sympy missing", err)
        self.assertFalse((self.root / self.OWN).exists())
        self.assertTrue((self.root / self.OTHER).exists())

    def test_failure_leaves_no_saved_grade_output_so_pr_body_stops(self):
        script = self.make_grade(1)
        self.invoke("grade", "math-z", "claude-fable-5-2", grade_script=script)
        self.assertFalse((self.root / ".bench-run/mz_claude_fable_5_2.grade.txt").exists())
        code, out, _ = self.invoke("pr-body", "math-z", "claude-fable-5-2", "5")
        self.assertEqual(code, 1)

    def test_failure_removes_a_stale_saved_grade_output(self):
        bench = self.root / ".bench-run"
        bench.mkdir()
        (bench / "mz_claude_fable_5_2.grade.txt").write_text("old")
        self.invoke("grade", "math-z", "claude-fable-5-2", grade_script=self.make_grade(1))
        self.assertFalse((bench / "mz_claude_fable_5_2.grade.txt").exists())

    def test_failure_with_no_own_sidecar_is_fine(self):
        code, _, _ = self.invoke("grade", "math-z", "claude-fable-5-2",
                                 grade_script=self.make_grade(1))
        self.assertEqual(code, 1)

    def test_ungraded_prompt_is_a_stop_and_grade_is_not_run(self):
        script = self.make_grade(0)
        code, out, _ = self.invoke("grade", "game-x", "claude-fable-5-2", grade_script=script)
        self.assertEqual(code, 1)
        self.assertIn("STOP: ", out)
        self.assertIn("no [grading] rule", out)


class GradeModeIsInteractiveOnlyTest(unittest.TestCase):
    def test_grade_is_not_on_the_child_allowlist_because_no_arm_prompt_is_graded(self):
        self.assertFalse([r for r in bra.ALLOWED_TOOLS if "bench_run.py grade" in r])


class MergeGateAcceptsRenderedNamesTest(unittest.TestCase):
    """The titles and branches this package renders must pass merge_results' gate."""

    def plan_lines(self, pid):
        # resolve() carries no overwrite checks, so this keeps passing once the arm's results exist.
        return dict(br.plan_fields(br.resolve(REPO, pid, "claude-fable-5-2")))

    def test_parse_title_accepts_the_rendered_pr_title_for_every_arm_prompt(self):
        for pid in bra.ARM_PROMPTS:
            with self.subTest(pid=pid):
                lines = self.plan_lines(pid)
                parsed = merge_results.parse_title(lines["pr_title"])
                self.assertEqual(parsed, (lines["prefix"], "claude-fable-5-2"))

    def test_gate_branch_regex_accepts_the_rendered_branch_for_every_arm_prompt(self):
        prompts = merge_results.load_prompt_files(REPO / "prompts")
        for pid in bra.ARM_PROMPTS:
            with self.subTest(pid=pid):
                lines = self.plan_lines(pid)
                branch = lines["branch"].replace("<N>", "123")
                pr = {"title": lines["pr_title"], "headRefName": branch, "isDraft": False,
                      "files": []}
                reasons = merge_results.gate(pr, [], set(), prompts, "claude-fable-5-2",
                                             merge_results.model_tag("claude-fable-5-2"))
                self.assertFalse([r for r in reasons if "title" in r or "branch" in r], reasons)

    def test_gate_rejects_a_branch_that_deviates_from_the_rendered_shape(self):
        prompts = merge_results.load_prompt_files(REPO / "prompts")
        lines = self.plan_lines("game-melon-jelly")
        pr = {"title": lines["pr_title"], "headRefName": "feat/123-melon-jelly-result",
              "isDraft": False, "files": []}
        reasons = merge_results.gate(pr, [], set(), prompts, "claude-fable-5-2",
                                     merge_results.model_tag("claude-fable-5-2"))
        self.assertTrue([r for r in reasons if "branch" in r])


class ScriptEntryTest(unittest.TestCase):
    def test_runs_as_a_script_from_the_repo_root_without_a_pythonpath(self):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        proc = subprocess.run([sys.executable, "harness/bench_run.py", "prompt", "no-such", "m"],
                              cwd=REPO, capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 1)
        self.assertTrue(proc.stdout.startswith("STOP: "), proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
