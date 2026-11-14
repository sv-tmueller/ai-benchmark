"""Unit tests for ``bench_run_all.py``, the batch driver behind ``/bench-run``.

No test here may reach the real ``claude`` binary. Children are started
through a fake ``claude`` executable written into a temp dir; ``git`` and
``gh`` go through the helper's single ``_run`` seam, which the tests patch.
"""

import base64
import contextlib
import fcntl
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from harness import bench_run_all as bra

REPO = Path(__file__).resolve().parents[2]
EFFORT_HELP = "Usage: claude [options]\n  --effort <level>   Effort level (low, medium, high, xhigh, max)\n"

FAKE_CLAUDE = r'''#!{python}
import json, os, sys, time
d = os.environ["FAKE_CLAUDE_DIR"]
argv = sys.argv[1:]
sc = json.load(open(os.path.join(d, "scenario.json")))
if argv == ["--help"]:
    sys.stdout.write(sc.get("help", ""))
    sys.exit(0)
slash = argv[argv.index("-p") + 1] if "-p" in argv else ""
pid = slash.split()[1] if len(slash.split()) > 1 else ""
beh = dict(sc.get("default", {}))
beh.update(sc.get("by_prompt", {}).get(pid, {}))
try:
    st0 = json.load(open(os.path.join(d, "state.json")))
    start_tree = st0["trees"].get(os.path.realpath(os.getcwd()))
except FileNotFoundError:
    start_tree = None
with open(os.path.join(d, "calls.jsonl"), "a") as f:
    f.write(json.dumps({
        "argv": argv, "cwd": os.getcwd(), "env_names": sorted(os.environ),
        "start_tree": start_tree,
        "effort": os.environ.get("CLAUDE_EFFORT"),
        "stdin_is_devnull": os.path.samestat(os.fstat(0), os.stat(os.devnull)),
        "sid": os.getpgrp() == os.getpid(),
    }) + "\n")
eff = beh.get("effects", {})
if eff:
    sp = os.path.join(d, "state.json")
    st = json.load(open(sp))
    if eff.get("open_pr"):
        n = st["next_pr"]
        st["next_pr"] = n + 1
        stem = os.path.splitext(os.path.basename(sc["files"][pid]))[0]
        pr = {"number": n, "url": "https://example.test/pull/%d" % n,
              "files": [{"path": sc["files"][pid]}],
              "headRefName": "feat/%d-%s-result" % (n, stem.replace("_", "-")),
              "state": "OPEN", "isCrossRepository": False,
              "body": "## Summary\n\ntext\n\nCloses #%d\n" % n}
        pr.update(eff.get("pr_extra", {}))
        st["prs"].append(pr)
    for rel in eff.get("write", []):
        path = sc["files"][pid] if rel == "{target}" else rel
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write("SECRET-DELIVERABLE")
    tree = st["trees"][os.path.realpath(os.getcwd())]  # the tree this child runs in
    if "branch" in eff:
        tree["branch"] = eff["branch"]
    if "dirty_tracked" in eff:
        tree["dirty_tracked"] = eff["dirty_tracked"]
    if eff.get("commit"):
        tree["head"] = "child-commit"
    if "origin_main" in eff:
        st["origin_main"] = eff["origin_main"]
    json.dump(st, open(sp, "w"))
if beh.get("sleep"):
    time.sleep(beh["sleep"])
if "stdout_raw" in beh:
    sys.stdout.write(beh["stdout_raw"])
else:
    sys.stdout.write(json.dumps(beh.get("json", {"type": "result", "result": "ok"})))
sys.exit(beh.get("exit", 0))
'''


USAGE = {"input_tokens": 28, "output_tokens": 77902,
         "cache_read_input_tokens": 1082945, "cache_creation_input_tokens": 109699}


def result_json(text="ok", **kw):
    d = {"type": "result", "subtype": "success", "is_error": False, "result": text,
         "permission_denials": [], "modelUsage": {"claude-fable-5-2": {}},
         "usage": dict(USAGE), "duration_ms": 821274, "total_cost_usd": 5.088076999999998}
    d.update(kw)
    return d


class FakeClaudeCase(unittest.TestCase):
    """Base: a temp dir holding a fake claude and its scenario/call log."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.bin = self.dir / "claude"
        self.bin.write_text(FAKE_CLAUDE.replace("{python}", sys.executable))
        self.bin.chmod(self.bin.stat().st_mode | stat.S_IXUSR)
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        self.env = {
            # The fake has an absolute shebang, so a bare `claude` must find only the fake.
            "PATH": str(self.dir), "HOME": str(self.dir),
            "FAKE_CLAUDE_DIR": str(self.dir), "CLAUDE_EFFORT": "high",
        }
        self.scenario({"help": EFFORT_HELP})

    def scenario(self, sc):
        (self.dir / "scenario.json").write_text(json.dumps(sc))

    def calls(self):
        p = self.dir / "calls.jsonl"
        if not p.exists():
            return []
        return [json.loads(line) for line in p.read_text().splitlines()]


class BuildCommandTest(unittest.TestCase):
    def cmd(self):
        return bra.build_command("claude", "/bench-run game-melon-jelly", "claude-fable-5-2", "high")

    def test_prompt_comes_right_after_dash_p(self):
        cmd = self.cmd()
        self.assertEqual(cmd[:3], ["claude", "-p", "/bench-run game-melon-jelly"])

    def test_model_effort_tools_mode_and_format_flags(self):
        cmd = self.cmd()
        for flag, value in (("--model", "claude-fable-5-2"), ("--effort", "high"),
                            ("--tools", "Bash,Write"), ("--permission-mode", "dontAsk"),
                            ("--output-format", "json")):
            self.assertEqual(cmd[cmd.index(flag) + 1], value, flag)

    def test_allowed_tools_is_last_and_one_rule_per_argument(self):
        cmd = self.cmd()
        rules = cmd[cmd.index("--allowedTools") + 1:]
        self.assertEqual(tuple(rules), bra.ALLOWED_TOOLS)
        self.assertIn("Edit(results/**)", rules)
        self.assertIn("Bash(git push -u origin feat/*)", rules)

    def test_write_is_enabled_as_an_edit_rule_never_a_write_rule(self):
        self.assertFalse([r for r in bra.ALLOWED_TOOLS if r.startswith("Write")])

    def test_no_merge_read_or_fetch_rule_and_no_bypass_flags(self):
        joined = " ".join(self.cmd())
        for banned in ("gh pr merge", "Read", "WebFetch", "bypassPermissions",
                       "dangerously", "skip-permissions", "--append-system-prompt",
                       "--fallback-model", "--max-turns"):
            self.assertNotIn(banned, joined)

    def test_only_the_planned_flags_appear(self):
        flags = [a for a in self.cmd() if a.startswith("--")]
        self.assertEqual(flags, ["--model", "--effort", "--tools", "--permission-mode",
                                 "--output-format", "--allowedTools"])


class BuildEnvTest(unittest.TestCase):
    def test_session_variables_are_removed_and_the_rest_kept(self):
        env = {
            "PATH": "/bin", "HOME": "/h", "GH_TOKEN": "t", "ANTHROPIC_API_KEY": "k",
            "CLAUDE_EFFORT": "high", "CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "s",
            "CLAUDE_CODE_CHILD_SESSION": "1", "CLAUDE_CODE_SESSION_ATTENDED": "1",
            "CLAUDE_PID": "1", "CLAUDE_CODE_INVOKED_SKILLS": "x",
            "CLAUDE_CODE_ENTRYPOINT": "cli", "CLAUDE_CODE_MESSAGING_SOCKET": "x",
            "CLAUDE_CODE_MESSAGING_FOO": "y", "CLAUDE_CONFIG_DIR": "/c",
        }
        out = bra.build_env(env)
        self.assertEqual(
            out, {"PATH": "/bin", "HOME": "/h", "GH_TOKEN": "t",
                  "ANTHROPIC_API_KEY": "k", "CLAUDE_CONFIG_DIR": "/c"})

    def test_input_mapping_is_not_mutated(self):
        env = {"CLAUDE_EFFORT": "high"}
        bra.build_env(env)
        self.assertEqual(env, {"CLAUDE_EFFORT": "high"})


class CheckModelTest(unittest.TestCase):
    def test_aliases_are_rejected(self):
        for alias in ("fable", "opus", "sonnet", "haiku", "Opus"):
            with self.subTest(alias=alias):
                self.assertIn("alias", bra.check_model(alias))

    def test_empty_and_unusable_ids_are_rejected(self):
        for bad in ("", "  ", "5-2"):
            with self.subTest(bad=bad):
                self.assertTrue(bra.check_model(bad))

    def test_exact_ids_pass(self):
        for good in ("claude-fable-5-2", "claude-opus-4-8", "claude-haiku-4-5-20251001"):
            with self.subTest(good=good):
                self.assertIsNone(bra.check_model(good))


class CheckEffortTest(FakeClaudeCase):
    def test_valid_level_with_effort_flag_passes(self):
        self.assertIsNone(bra.check_effort(str(self.bin), self.env))
        self.assertEqual(self.calls(), [])  # only --help ran; --help is not logged

    def test_every_level_is_accepted(self):
        for level in ("low", "medium", "high", "xhigh", "max"):
            with self.subTest(level=level):
                env = dict(self.env, CLAUDE_EFFORT=level)
                self.assertIsNone(bra.check_effort(str(self.bin), env))

    def test_unset_variable_stops(self):
        env = {k: v for k, v in self.env.items() if k != "CLAUDE_EFFORT"}
        self.assertIn("CLAUDE_EFFORT", bra.check_effort(str(self.bin), env))

    def test_empty_variable_stops(self):
        env = dict(self.env, CLAUDE_EFFORT="")
        self.assertIn("CLAUDE_EFFORT", bra.check_effort(str(self.bin), env))

    def test_unknown_level_stops(self):
        env = dict(self.env, CLAUDE_EFFORT="ultra")
        self.assertIn("ultra", bra.check_effort(str(self.bin), env))

    def test_missing_effort_flag_in_help_stops(self):
        self.scenario({"help": "Usage: claude [options]\n  --model <m>\n"})
        self.assertIn("--effort", bra.check_effort(str(self.bin), self.env))

    def test_missing_binary_stops_instead_of_raising(self):
        msg = bra.check_effort(str(self.dir / "nope"), self.env)
        self.assertIn("cannot run", msg)


class SummarizeTest(unittest.TestCase):
    def summarize(self, payload, exit_code=0, timed_out=False, stdout=None, model="claude-fable-5-2"):
        raw = json.dumps(payload) if stdout is None else stdout
        return bra.summarize(bra.ChildRun(exit_code, timed_out, raw, ""), model)

    def test_stop_line_is_taken_from_the_result_text(self):
        out = self.summarize(result_json("noise\nSTOP: results/x.html already exists on disk\nmore"))
        self.assertEqual(out.stop_line, "STOP: results/x.html already exists on disk")

    def test_void_marker_line_is_taken_from_the_result_text(self):
        out = self.summarize(result_json("secret deliverable body\nrun void, re-run in a fresh session"))
        self.assertEqual(out.void_line, "run void, re-run in a fresh session")

    def test_nothing_else_of_the_result_text_is_kept(self):
        out = self.summarize(result_json("SECRET-DELIVERABLE\nSTOP: x"))
        self.assertNotIn("SECRET", repr(out))

    def test_denied_tools_are_names_only_and_tool_input_is_dropped(self):
        denials = [{"tool_name": "Read", "tool_input": {"content": "SECRET"}},
                   {"tool_name": "Bash", "tool_input": {"command": "gh pr merge"}},
                   {"tool_name": "Read", "tool_input": {}}]
        out = self.summarize(result_json(permission_denials=denials))
        self.assertEqual(out.denied_tools, ["Bash", "Read"])
        self.assertNotIn("SECRET", repr(out))
        self.assertNotIn("gh pr merge", repr(out))

    def test_model_usage_keys_are_logged_and_flag_a_missing_model(self):
        out = self.summarize(result_json(modelUsage={"claude-opus-4-8": {}}))
        self.assertEqual(out.model_usage, ["claude-opus-4-8"])
        self.assertFalse(out.model_ok)
        self.assertTrue(self.summarize(result_json()).model_ok)

    def test_error_and_subtype_come_from_the_json(self):
        out = self.summarize(result_json(is_error=True, subtype="error_during_execution"), exit_code=1)
        self.assertTrue(out.is_error)
        self.assertEqual(out.subtype, "error_during_execution")
        self.assertEqual(out.exit_code, 1)

    def test_an_event_list_uses_its_result_entry(self):
        events = [{"type": "system"}, result_json("STOP: x"), {"type": "other"}]
        self.assertEqual(self.summarize(events).stop_line, "STOP: x")

    def test_usable_usage_is_kept_as_the_six_metrics_and_the_text_is_still_dropped(self):
        out = self.summarize(result_json("SECRET-DELIVERABLE"))
        self.assertEqual(out.metrics["output_tokens"], 77902)
        self.assertEqual(out.metrics["duration_seconds"], 821.3)
        self.assertNotIn("SECRET", repr(out))

    def test_unusable_usage_leaves_no_metrics(self):
        self.assertIsNone(self.summarize(result_json(usage=None)).metrics)

    def test_a_timed_out_child_has_no_metrics_even_with_parseable_output(self):
        self.assertIsNone(self.summarize(result_json(), timed_out=True).metrics)

    def test_unparseable_output_has_no_metrics(self):
        self.assertIsNone(self.summarize(None, stdout="not json").metrics)

    def test_unparseable_output_gives_no_json_and_no_text(self):
        out = self.summarize(None, stdout="not json SECRET")
        self.assertFalse(out.parsed)
        self.assertIsNone(out.stop_line)
        self.assertNotIn("SECRET", repr(out))


class RunMetricsTest(unittest.TestCase):
    def test_the_six_values_are_converted_and_rounded_in_contract_order(self):
        out = bra.run_metrics(result_json())
        self.assertEqual(list(out), ["duration_seconds", "input_tokens", "output_tokens",
                                     "cache_read_tokens", "cache_write_tokens", "cost_usd"])
        self.assertEqual(out, {"duration_seconds": 821.3, "input_tokens": 28,
                               "output_tokens": 77902, "cache_read_tokens": 1082945,
                               "cache_write_tokens": 109699, "cost_usd": 5.088077})

    def test_whole_number_duration_and_cost_are_accepted(self):
        out = bra.run_metrics(result_json(duration_ms=2000, total_cost_usd=3))
        self.assertEqual((out["duration_seconds"], out["cost_usd"]), (2.0, 3.0))

    def test_zero_tokens_in_some_fields_are_usable_when_the_sum_is_positive(self):
        usage = {"input_tokens": 0, "output_tokens": 5,
                 "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
        out = bra.run_metrics(result_json(usage=usage, duration_ms=0, total_cost_usd=0))
        self.assertEqual(out["output_tokens"], 5)

    def test_extra_and_unknown_fields_do_not_matter(self):
        usage = dict(USAGE, server_tool_use={"web_search_requests": 0}, service_tier="standard")
        out = bra.run_metrics(result_json(usage=usage, is_error=True, subtype="x", extra=1))
        self.assertIsNotNone(out)

    def test_unusable_data_gives_none_and_never_a_partial_result(self):
        def without(key):
            d = result_json()
            del d[key]
            return d

        def with_usage(**kw):
            return result_json(usage=dict(USAGE, **kw))

        def without_usage(key):
            d = result_json()
            del d["usage"][key]
            return d

        cases = {
            "not a dict": None,
            "a list": [result_json()],
            "usage missing": without("usage"),
            "usage not a dict": result_json(usage=[1, 2, 3, 4]),
            "duration missing": without("duration_ms"),
            "cost missing": without("total_cost_usd"),
            "input missing": without_usage("input_tokens"),
            "output missing": without_usage("output_tokens"),
            "cache read missing": without_usage("cache_read_input_tokens"),
            "cache write missing": without_usage("cache_creation_input_tokens"),
            "token as string": with_usage(output_tokens="77902"),
            "token as float": with_usage(output_tokens=1.5),
            "token as bool": with_usage(input_tokens=True),
            "negative token": with_usage(cache_read_input_tokens=-1),
            "token None": with_usage(output_tokens=None),
            "duration as string": result_json(duration_ms="821274"),
            "duration as bool": result_json(duration_ms=True),
            "negative duration": result_json(duration_ms=-1),
            "nan duration": result_json(duration_ms=float("nan")),
            "inf duration": result_json(duration_ms=float("inf")),
            "cost as string": result_json(total_cost_usd="5.08"),
            "cost as bool": result_json(total_cost_usd=False),
            "negative cost": result_json(total_cost_usd=-0.01),
            "nan cost": result_json(total_cost_usd=float("nan")),
            "inf cost": result_json(total_cost_usd=float("inf")),
            "all-zero usage (API error before any model call)": result_json(
                usage={"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                       "cache_creation_input_tokens": 0}, total_cost_usd=0, is_error=True),
        }
        for label, data in cases.items():
            with self.subTest(label):
                self.assertIsNone(bra.run_metrics(data))


class MetricsSectionTest(unittest.TestCase):
    METRICS = {"duration_seconds": 821.3, "input_tokens": 28, "output_tokens": 77902,
               "cache_read_tokens": 1082945, "cache_write_tokens": 109699, "cost_usd": 5.088077}
    PATH = "results/melon-jelly/melon-jelly_claude_fable_5_2_high.run.json"

    def test_the_usable_section_shows_duration_output_tokens_cost_and_the_breakdown(self):
        text = bra.metrics_section(self.METRICS, self.PATH)
        self.assertTrue(text.startswith("<!-- run-metrics -->\n## Run metrics\n"))
        self.assertTrue(text.endswith("<!-- /run-metrics -->"))
        self.assertIn("Duration 821.3 s, 77,902 output tokens, cost 5.088077 USD.", text)
        for row in ("| Input | 28 |", "| Output | 77,902 |",
                    "| Cache read | 1,082,945 |", "| Cache write | 109,699 |"):
            self.assertIn(row, text)
        self.assertIn("`%s`" % self.PATH, text)
        self.assertIn("harness/bench_run_all.py", text)

    def test_a_short_duration_and_a_small_cost_keep_their_fixed_decimals(self):
        text = bra.metrics_section(dict(self.METRICS, duration_seconds=2.0, cost_usd=0.5), self.PATH)
        self.assertIn("Duration 2.0 s,", text)
        self.assertIn("cost 0.500000 USD.", text)

    def test_the_unavailable_section_says_so_and_names_no_run_file(self):
        text = bra.metrics_section(None, self.PATH)
        self.assertEqual(text, (
            "<!-- run-metrics -->\n## Run metrics\n\n"
            "Unavailable: the JSON output of the batch session that generated this result "
            "carried no usable usage data, so no run file was written.\n"
            "<!-- /run-metrics -->"))


class SpliceSectionTest(unittest.TestCase):
    SECTION = "<!-- run-metrics -->\n## Run metrics\n\nbody\n<!-- /run-metrics -->"
    BODY = "## Summary\n\ntext\n\n## In-session caveats\n\nnotes\n\nCloses #315\n\nfooter\n"

    def test_the_section_goes_in_front_of_the_closes_line(self):
        out = bra.splice_section(self.BODY, self.SECTION)
        self.assertEqual(out, "## Summary\n\ntext\n\n## In-session caveats\n\nnotes\n\n"
                              + self.SECTION + "\n\nCloses #315\n\nfooter\n")

    def test_without_a_closes_line_the_section_is_appended(self):
        out = bra.splice_section("## Summary\n\ntext\n", self.SECTION)
        self.assertEqual(out, "## Summary\n\ntext\n\n" + self.SECTION + "\n")

    def test_a_closes_mention_inside_a_line_is_not_the_anchor(self):
        body = "This PR Closes #1 sometimes.\n\nmore\n"
        self.assertTrue(bra.splice_section(body, self.SECTION).endswith(self.SECTION + "\n"))

    def test_an_empty_body_becomes_just_the_section(self):
        self.assertEqual(bra.splice_section("", self.SECTION), self.SECTION + "\n")
        self.assertEqual(bra.splice_section(None, self.SECTION), self.SECTION + "\n")

    def test_a_second_application_replaces_the_span_between_the_markers(self):
        first = bra.splice_section(self.BODY, self.SECTION)
        newer = "<!-- run-metrics -->\n## Run metrics\n\nnewer\n<!-- /run-metrics -->"
        second = bra.splice_section(first, newer)
        self.assertEqual(second.count("<!-- run-metrics -->"), 1)
        self.assertEqual(second.count("<!-- /run-metrics -->"), 1)
        self.assertIn("newer", second)
        self.assertNotIn("\nbody\n", second)
        self.assertEqual(second, self.BODY.replace("Closes #315", newer + "\n\nCloses #315"))

    def test_applying_the_same_section_twice_changes_nothing(self):
        once = bra.splice_section(self.BODY, self.SECTION)
        self.assertEqual(bra.splice_section(once, self.SECTION), once)

    def test_a_lone_start_marker_is_not_a_span(self):
        body = "<!-- run-metrics -->\nstray\n\nCloses #4\n"
        out = bra.splice_section(body, self.SECTION)
        self.assertEqual(out.count("<!-- /run-metrics -->"), 1)
        self.assertIn("stray", out)


class LaunchTest(FakeClaudeCase):
    def launch(self, **kw):
        args = dict(claude_bin=str(self.bin), slash="/bench-run game-melon-jelly",
                    model="claude-fable-5-2", effort="high", timeout=30,
                    repo_root=self.repo, environ=self.env)
        args.update(kw)
        return bra.launch(**args)

    def test_child_gets_the_built_command_cwd_and_closed_stdin(self):
        self.scenario({"help": EFFORT_HELP, "default": {"json": result_json()}})
        run = self.launch()
        self.assertEqual(run.exit_code, 0)
        self.assertFalse(run.timed_out)
        (call,) = self.calls()
        self.assertEqual(call["argv"], bra.build_command("claude", "/bench-run game-melon-jelly",
                                                         "claude-fable-5-2", "high")[1:])
        self.assertEqual(Path(call["cwd"]).resolve(), self.repo.resolve())
        self.assertTrue(call["stdin_is_devnull"])

    def test_child_leads_its_own_process_group(self):
        self.launch()
        (call,) = self.calls()
        self.assertTrue(call["sid"])

    def test_child_environment_has_no_inherited_session_variables(self):
        env = dict(self.env, CLAUDECODE="1", CLAUDE_CODE_SESSION_ID="s", CLAUDE_CODE_MESSAGING_X="y")
        self.launch(environ=env)
        (call,) = self.calls()
        names = set(call["env_names"])
        self.assertTrue({"CLAUDE_EFFORT", "CLAUDECODE", "CLAUDE_CODE_SESSION_ID",
                         "CLAUDE_CODE_MESSAGING_X"}.isdisjoint(names))
        self.assertIn("FAKE_CLAUDE_DIR", names)
        self.assertIsNone(call["effort"])

    def test_a_bare_claude_resolves_to_the_fake(self):
        # Guard first: if this fails, nothing is launched.
        self.assertEqual(os.get_exec_path(bra.build_env(self.env)), [str(self.dir)])
        self.scenario({"help": EFFORT_HELP, "default": {"json": result_json("fake-was-called")}})
        run = self.launch(claude_bin="claude")
        self.assertEqual(run.exit_code, 0, run.stderr)
        (call,) = self.calls()
        self.assertEqual(call["argv"][:2], ["-p", "/bench-run game-melon-jelly"])
        self.assertEqual(json.loads(run.stdout)["result"], "fake-was-called")

    def test_nonzero_exit_is_reported(self):
        self.scenario({"help": EFFORT_HELP, "default": {"exit": 3}})
        self.assertEqual(self.launch().exit_code, 3)

    def test_timeout_kills_the_child_and_returns_quickly(self):
        self.scenario({"help": EFFORT_HELP, "default": {"sleep": 60}})
        start = time.monotonic()
        run = self.launch(timeout=1)
        self.assertTrue(run.timed_out)
        self.assertLess(time.monotonic() - start, 20)

    def test_only_the_given_fds_are_passed_to_the_child(self):
        fd = os.open(os.devnull, os.O_RDONLY)
        self.addCleanup(os.close, fd)
        with mock.patch.object(bra.subprocess, "Popen", wraps=subprocess.Popen) as popen:
            self.launch()
            self.launch(pass_fds=(fd,))
        self.assertEqual([c.kwargs["pass_fds"] for c in popen.call_args_list], [(), (fd,)])

    def test_missing_binary_is_reported_not_raised(self):
        run = self.launch(claude_bin=str(self.dir / "nope"))
        self.assertIsNotNone(run.exit_code)
        self.assertNotEqual(run.exit_code, 0)


class SmokeTest(FakeClaudeCase):
    def run_main(self, argv, run=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(bra, "_run", run or self.no_git):
            code = bra.main(argv, environ=self.env, repo_root=self.repo)
        return code, out.getvalue()

    @staticmethod
    def no_git(cmd, **kw):
        raise AssertionError("smoke must not call git or gh: %r" % (cmd,))

    def argv(self, *extra):
        return ["--model", "claude-fable-5-2", "--claude", str(self.bin),
                "--log-dir", str(self.dir / "logs"), *extra]

    def test_smoke_starts_exactly_one_dry_run_child(self):
        self.scenario({"help": EFFORT_HELP, "default": {"json": result_json("path preview")}})
        code, out = self.run_main(self.argv("--smoke", "game-melon-jelly"))
        self.assertEqual(code, 0)
        (call,) = self.calls()
        self.assertEqual(call["argv"][call["argv"].index("-p") + 1],
                         "/bench-run game-melon-jelly --dry-run")
        self.assertIn("path preview", out)

    def test_smoke_prints_exit_subtype_denied_tool_names_and_model_usage(self):
        payload = result_json("x", is_error=True, subtype="error_max_turns",
                              permission_denials=[{"tool_name": "Read", "tool_input": {"p": "SECRET"}}],
                              modelUsage={"claude-fable-5-2": {}})
        self.scenario({"help": EFFORT_HELP, "default": {"json": payload, "exit": 1}})
        code, out = self.run_main(self.argv("--smoke", "game-melon-jelly"))
        self.assertNotEqual(code, 0)
        self.assertIn("exit_code: 1", out)
        self.assertIn("subtype: error_max_turns", out)
        self.assertIn("denied_tools: Read", out)
        self.assertIn("claude-fable-5-2", out)
        self.assertNotIn("SECRET", out)

    def test_smoke_stops_before_any_child_when_effort_is_missing(self):
        del self.env["CLAUDE_EFFORT"]
        code, out = self.run_main(self.argv("--smoke", "game-melon-jelly"))
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"(?m)^STOP: .*CLAUDE_EFFORT")
        self.assertEqual(self.calls(), [])

    def test_smoke_stops_before_any_child_for_an_alias(self):
        code, out = self.run_main(["--model", "fable", "--claude", str(self.bin),
                                   "--log-dir", str(self.dir / "logs"),
                                   "--smoke", "game-melon-jelly"])
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"(?m)^STOP: .*alias")
        self.assertEqual(self.calls(), [])

    def test_smoke_rejects_a_prompt_outside_the_arm(self):
        code, out = self.run_main(self.argv("--smoke", "math-addition"))
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"(?m)^STOP: .*math-addition")
        self.assertEqual(self.calls(), [])

    def test_smoke_writes_the_child_output_to_the_log_folder(self):
        self.scenario({"help": EFFORT_HELP, "default": {"json": result_json("logged")}})
        self.run_main(self.argv("--smoke", "game-melon-jelly"))
        logs = list((self.dir / "logs").glob("game-melon-jelly*"))
        self.assertTrue(logs)


class FakeGit:
    """Stands in for ``git`` and ``gh`` behind the helper's ``_run`` seam.

    Every checkout has a tree: the main repo and each worktree that
    ``git worktree add`` registered. The working-tree state of a tree is its
    real temp directory (untracked = any file outside ``prompts/``,
    ``harness/`` and the git-ignored ``.bench-run/``, and for the main repo
    ``.claude/worktrees/``); its branch, head and tracked changes live in
    ``state.json``, which the fake claude changes too, for the tree it runs
    in. ``origin_main``, the PRs and ``gh`` state are shared by all trees,
    like the refs of a real clone. A command resolves to the nearest tree at
    or above its ``cwd``, so a git call in an unregistered folder under the
    repo lands on the main checkout, as real git would.
    """

    def __init__(self, case):
        self.case = case
        self.calls = []  # every command, in order
        self.cwds = []   # the resolved cwd of each command, parallel to calls

    @property
    def main_root(self):
        return self.case.repo.resolve()

    def state(self):
        return json.loads((self.case.dir / "state.json").read_text())

    def save(self, st):
        (self.case.dir / "state.json").write_text(json.dumps(st))

    def init(self, **overrides):
        st = {"origin_main": "abc", "gh_ok": True, "main_files": [], "prs": [], "next_pr": 1,
              "gh_fail": {}, "puts": [], "edits": [],
              "trees": {str(self.main_root): {"branch": "main", "head": "abc", "dirty_tracked": []}},
              "worktrees": [], "unmerged": ["child-commit"]}
        st.update(overrides)
        self.save(st)

    def set_main(self, **fields):
        """Change the main checkout's ``branch``, ``head`` or ``dirty_tracked``."""
        self.set_tree(self.main_root, **fields)

    def set_tree(self, root, **fields):
        st = self.state()
        st["trees"][str(Path(root).resolve())].update(fields)
        self.save(st)

    def set_shared(self, **fields):
        st = self.state()
        st.update(fields)
        self.save(st)

    def tree(self, root=None):
        return self.state()["trees"][str(Path(root or self.main_root).resolve())]

    def register(self, root, branch="", head="abc", dirty_tracked=()):
        """Register ``root`` as a worktree, as an earlier run would have left it."""
        root = Path(root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        for sub_dir in ("prompts", "harness"):  # the tracked files of a clean checkout
            if (self.main_root / sub_dir).is_dir() and not (root / sub_dir).exists():
                shutil.copytree(self.main_root / sub_dir, root / sub_dir)
        st = self.state()
        st["worktrees"].append(str(root))
        st["trees"][str(root)] = {"branch": branch, "head": head, "dirty_tracked": list(dirty_tracked)}
        self.save(st)

    def calls_in(self, root):
        root = Path(root).resolve()
        return [c for c, w in zip(self.calls, self.cwds) if w == root]

    @staticmethod
    def done(out="", rc=0, err=""):
        return subprocess.CompletedProcess([], rc, out, err)

    @staticmethod
    def root_of(st, cwd):
        here = Path(cwd).resolve()
        for cand in (here, *here.parents):
            if str(cand) in st["trees"]:
                return cand
        raise AssertionError("git ran outside every tree: %s" % cwd)

    def untracked(self, root=None):
        root = Path(root or self.main_root).resolve()
        skip = ["prompts/", "harness/", ".bench-run/"]
        if root == self.main_root:
            skip.append(".claude/worktrees/")
        found = []
        for p in sorted(root.rglob("*")):
            rel = p.relative_to(root).as_posix()
            if p.is_file() and not rel.startswith(tuple(skip)):
                found.append(rel)
        return found

    def worktree(self, cmd, st, root):
        sub = cmd[2]
        if sub == "list":
            out = "worktree %s\nHEAD %s\nbranch refs/heads/%s\n\n" % (
                self.main_root, st["trees"][str(self.main_root)]["head"],
                st["trees"][str(self.main_root)]["branch"])
            for path in st["worktrees"]:
                out += "worktree %s\nHEAD %s\ndetached\n" % (path, st["trees"][path]["head"])
                if not Path(path).exists():
                    out += "prunable gitdir file points to non-existent location\n"
                out += "\n"
            return self.done(out)
        if sub == "add":
            path = Path(cmd[4]).resolve()
            if str(path) in st["worktrees"]:
                return self.done(rc=128, err="fatal: '%s' is a missing but already registered worktree;\n" % path)
            if path.exists() and any(path.iterdir()):
                return self.done(rc=128, err="fatal: '%s' already exists\n" % path)
            path.mkdir(parents=True, exist_ok=True)
            for sub_dir in ("prompts", "harness"):
                if (self.main_root / sub_dir).is_dir():
                    shutil.copytree(self.main_root / sub_dir, path / sub_dir)
            st["worktrees"].append(str(path))
            st["trees"][str(path)] = {"branch": "", "head": st["origin_main"], "dirty_tracked": []}
            self.save(st)
            return self.done()
        if sub == "remove":
            path = Path(cmd[-1]).resolve()
            if str(path) not in st["worktrees"]:
                return self.done(rc=128, err="fatal: '%s' is not a working tree\n" % path)
            if st["trees"][str(path)]["dirty_tracked"] or self.untracked(path):
                if "--force" not in cmd:
                    return self.done(rc=128, err="fatal: '%s' contains modified or untracked files, "
                                                 "use --force to delete it\n" % path)
            shutil.rmtree(path)
            st["worktrees"].remove(str(path))
            del st["trees"][str(path)]
            self.save(st)
            return self.done()
        if sub == "prune":
            for path in [p for p in st["worktrees"] if not Path(p).exists()]:
                st["worktrees"].remove(path)
                del st["trees"][path]
            self.save(st)
            return self.done()
        raise AssertionError("unexpected worktree command %r" % (cmd,))

    def __call__(self, cmd, cwd=None, timeout=None):
        self.calls.append(list(cmd))
        st = self.state()
        self.cwds.append(Path(cwd).resolve() if cwd else None)
        if cmd[0] not in ("git", "gh"):
            return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        root = self.root_of(st, cwd or self.main_root)
        tree = st["trees"][str(root)]
        if cmd[:3] == ["git", "fetch", "origin"]:
            return self.done()
        if cmd == ["git", "branch", "--show-current"]:
            return self.done(tree["branch"] + "\n")
        if cmd == ["git", "rev-parse", "HEAD"]:
            return self.done(tree["head"] + "\n")
        if cmd == ["git", "rev-parse", "origin/main"]:
            return self.done(st["origin_main"] + "\n")
        if cmd == ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"]:
            return self.done(rc=1 if tree["head"] in st["unmerged"] else 0)
        if cmd == ["git", "rev-parse", "--show-toplevel"]:
            return self.done(str(root) + "\n")
        if cmd[:2] == ["git", "status"]:
            lines = [" M " + p for p in tree["dirty_tracked"]]
            if "--untracked-files=no" not in cmd:
                lines += ["?? " + p for p in self.untracked(root)]
            return self.done("".join(line + "\n" for line in lines))
        if cmd[:4] == ["git", "ls-tree", "-r", "--name-only"]:
            return self.done("".join(p + "\n" for p in st["main_files"]))
        if cmd == ["git", "switch", "--detach", "origin/main"]:
            tree["branch"], tree["head"] = "", st["origin_main"]
            self.save(st)
            return self.done()
        if cmd[:2] == ["git", "worktree"]:
            return self.worktree(cmd, st, root)
        if cmd == ["gh", "auth", "status"]:
            return self.done(rc=0 if st["gh_ok"] else 1, err="" if st["gh_ok"] else "not logged in")
        if cmd[:3] == ["gh", "pr", "list"]:
            return self.done(json.dumps(st["prs"]))
        if cmd[:3] == ["gh", "pr", "view"]:
            return self.pr_view(cmd, st)
        if cmd[:4] == ["gh", "api", "--method", "PUT"]:
            return self.contents_put(cmd, st)
        if cmd[:3] == ["gh", "pr", "edit"]:
            return self.pr_edit(cmd, st)
        raise AssertionError("unexpected command %r" % (cmd,))

    @staticmethod
    def failure(st, name):
        """The stderr to fail ``name`` with, or ``None``; set with ``set_shared(gh_fail={...})``."""
        message = st["gh_fail"].get(name)
        return None if message is None else FakeGit.done(rc=1, err=message)

    def pr_view(self, cmd, st):
        assert cmd[4:6] == ["--json", "state,isCrossRepository,headRefName,body,files"], cmd
        assert len(cmd) == 6, cmd
        if self.failure(st, "view"):
            return self.failure(st, "view")
        found = [p for p in st["prs"] if p["number"] == int(cmd[3])]
        if not found:
            return self.done(rc=1, err="no pull requests found\n")
        keys = cmd[5].split(",")
        return self.done(json.dumps({k: found[0][k] for k in keys}))

    def contents_put(self, cmd, st):
        """``gh api --method PUT repos/{owner}/{repo}/contents/<path> -f k=v ...``: one new file, one commit."""
        endpoint = cmd[4]
        prefix = "repos/{owner}/{repo}/contents/"
        assert endpoint.startswith(prefix), cmd
        rest = cmd[5:]
        assert len(rest) % 2 == 0 and all(a == "-f" for a in rest[::2]), cmd
        fields = dict(f.split("=", 1) for f in rest[1::2])
        assert sorted(fields) == ["branch", "content", "message"], cmd  # no sha: it must never overwrite
        if self.failure(st, "put"):
            return self.failure(st, "put")
        path = endpoint[len(prefix):]
        found = [p for p in st["prs"] if p.get("headRefName") == fields["branch"]]
        if not found or any(f["path"] == path for f in found[0]["files"]):
            return self.done(rc=1, err="HTTP 422: Invalid request.\n")
        found[0]["files"].append({"path": path})
        st["puts"].append({"path": path, "branch": fields["branch"], "message": fields["message"],
                           "content": base64.b64decode(fields["content"]).decode("utf-8")})
        self.save(st)
        return self.done("{}")

    def pr_edit(self, cmd, st):
        assert cmd[3:5] == [cmd[3], "--body-file"] and len(cmd) == 6, cmd
        if self.failure(st, "edit"):
            return self.failure(st, "edit")
        text = Path(cmd[5]).read_text(encoding="utf-8")
        for p in st["prs"]:
            if p["number"] == int(cmd[3]):
                p["body"] = text
        st["edits"].append({"number": int(cmd[3]), "body": text})
        self.save(st)
        return self.done()


def readme_ledger():
    """(prompt id, target path) rows of the README Fable 5.2 ledger table.

    Every path must carry the ``<effort>`` placeholder; it is filled in with
    ``high``, the effort level of the test session.
    """
    text = (REPO / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([a-z0-9-]+)` \|[^\n]*\| `(results/[^`]+)` \|", text, re.M)
    for _, path in rows:
        assert path.count("_<effort>.") == 1, path
    return [(pid, path.replace("<effort>", "high")) for pid, path in rows]


class BatchCase(FakeClaudeCase):
    def setUp(self):
        super().setUp()
        (self.repo / "prompts").mkdir()
        for p in (REPO / "prompts").glob("*.toml"):
            if not p.name.endswith(".fixtures.toml"):
                (self.repo / "prompts" / p.name).write_text(p.read_text(encoding="utf-8"))
        self.targets = dict(readme_ledger())
        self.git = FakeGit(self)
        self.git.init()
        self.wt = self.wt_for("high")
        self.set_children()

    def wt_for(self, effort, model="claude-fable-5-2"):
        return self.repo / ".claude" / "worktrees" / ("bench-run-%s_%s" % (model.replace("-", "_"), effort))

    def set_children(self, by_prompt=None, default=None, help_text=EFFORT_HELP):
        base = {"json": result_json("done"), "effects": {"open_pr": True}}
        base.update(default or {})
        self.scenario({"help": help_text, "files": self.targets,
                       "default": base, "by_prompt": by_prompt or {}})

    def batch(self, *extra, model="claude-fable-5-2", timeout="60", env=None, runner=None):
        argv = ["--model", model, "--claude", str(self.bin), "--timeout", timeout,
                "--log-dir", str(self.dir / "logs"), *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(bra, "_run", runner or self.git):
            code = bra.main(argv, environ=env or self.env, repo_root=self.repo)
        return code, out.getvalue()

    def report_lines(self, out):
        return {m.group(1): (m.group(2), m.group(3)) for m in
                re.finditer(r"(?m)^([a-z]+(?:-[a-z]+)+)  (.+?)  (\S+)$", out)}

    def called_ids(self):
        return [c["argv"][c["argv"].index("-p") + 1].split()[1] for c in self.calls()]


class ArmDataTest(unittest.TestCase):
    def test_arm_prompts_match_the_readme_ledger_in_order(self):
        self.assertEqual(list(bra.ARM_PROMPTS), [pid for pid, _ in readme_ledger()])
        self.assertEqual(len(bra.ARM_PROMPTS), 14)

    def test_each_arm_prompt_has_one_toml_with_prefix_and_save_as_and_no_images_or_grading(self):
        import tomllib
        tomls = [p for p in sorted((REPO / "prompts").glob("*.toml"))
                 if not p.name.endswith(".fixtures.toml")]
        data = [tomllib.loads(p.read_text(encoding="utf-8")) for p in tomls]
        for pid in bra.ARM_PROMPTS:
            with self.subTest(pid=pid):
                hits = [d for d in data if d.get("id") == pid]
                self.assertEqual(len(hits), 1)
                self.assertTrue(hits[0].get("file_prefix"))
                self.assertTrue(hits[0].get("save_as"))
                self.assertNotIn("images", hits[0])
                self.assertNotIn("grading", hits[0])

    def test_ledger_target_names_match_prefix_tag_and_extension(self):
        for pid, target in readme_ledger():
            with self.subTest(pid=pid):
                name = bra.expected_name(REPO, pid, "claude-fable-5-2", "high")
                self.assertEqual(Path(target).name, name)


    def test_no_prompt_is_called_all_so_the_skill_argument_all_cannot_collide(self):
        import tomllib
        self.assertNotIn("all", bra.ARM_PROMPTS)
        for path in sorted((REPO / "prompts").glob("*.toml")):
            if path.name.endswith(".fixtures.toml"):
                continue
            with self.subTest(file=path.name):
                data = tomllib.loads(path.read_text(encoding="utf-8"))
                self.assertNotEqual(path.stem.casefold(), "all")
                self.assertNotEqual(str(data.get("id", "")).casefold(), "all")


def arm(*numbers):
    """The arm prompt ids at the given 1-based positions."""
    return tuple(bra.ARM_PROMPTS[n - 1] for n in numbers)


class SelectionParseTest(unittest.TestCase):
    def test_all_in_any_case_selects_the_whole_arm(self):
        for text in ("all", "ALL", "All", "  all  "):
            with self.subTest(text=text):
                self.assertEqual(bra.parse_selection(text), bra.ARM_PROMPTS)

    def test_a_single_number_a_list_and_a_range(self):
        for text, want in (("2", arm(2)), ("1,4,7", arm(1, 4, 7)), ("3-6", arm(3, 4, 5, 6)),
                           ("1,3-5", arm(1, 3, 4, 5)), ("14", arm(14)), ("1-14", bra.ARM_PROMPTS)):
            with self.subTest(text=text):
                self.assertEqual(bra.parse_selection(text), want)

    def test_spaces_around_items_and_around_the_dash_are_allowed(self):
        self.assertEqual(bra.parse_selection(" 1 , 3 - 5 ,7"), arm(1, 3, 4, 5, 7))

    def test_repeats_and_overlaps_collapse_and_the_result_is_in_arm_order(self):
        self.assertEqual(bra.parse_selection("5,1,5,2-3"), arm(1, 2, 3, 5))
        self.assertEqual(bra.parse_selection("4-6,5,3-5"), arm(3, 4, 5, 6))

    def test_a_degenerate_range_selects_one_prompt(self):
        self.assertEqual(bra.parse_selection("4-4"), arm(4))

    def test_every_malformed_or_out_of_range_answer_is_rejected(self):
        for text in ("", "   ", "0", "15", "3-15", "0-3", "6-3", "1,,2", "1,", ",1", "-3", "3-",
                     "1-2-3", "all,3", "3,all", "1 3", "1.5", "x", "game-melon-jelly",
                     "first three", "٣", "1-٣", "１", "99999999999999999999",
                     "1" * 5000, "all all", "1;2", "1-"):
            with self.subTest(text=text[:20]):
                with self.assertRaises(bra.SelectionError):
                    bra.parse_selection(text)

    def test_a_selection_error_is_a_value_error_with_a_reason(self):
        with self.assertRaises(ValueError) as ctx:
            bra.parse_selection("15")
        self.assertIsInstance(ctx.exception, bra.SelectionError)
        self.assertIn("15", str(ctx.exception))


class SelectModeTest(BatchCase):
    def assert_read_only(self):
        self.assertEqual(self.git.calls, [])
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.repo / ".claude").exists())
        self.assertFalse((self.dir / "logs").exists())

    def test_a_valid_answer_prints_the_prompts_line_in_arm_order_and_starts_nothing(self):
        code, out = self.batch("--select", "1,3-5")
        self.assertEqual(code, 0, out)
        self.assertEqual(out, "prompts: game-melon-jelly,game-minecraft,scene-meridian-launch,"
                              "scene-sunset-ocean\n")
        self.assert_read_only()

    def test_a_scrambled_answer_comes_back_sorted_and_without_repeats(self):
        _, out = self.batch("--select", "3,1,3")
        self.assertEqual(out, "prompts: game-melon-jelly,game-minecraft\n")

    def test_selecting_everything_prints_prompts_all(self):
        for answer in ("all", "ALL", "1-14", "14,1-13"):
            with self.subTest(answer=answer):
                code, out = self.batch("--select", answer)
                self.assertEqual((code, out), (0, "prompts: all\n"))
        self.assert_read_only()

    def test_an_empty_or_unparseable_answer_is_invalid_with_exit_3(self):
        for answer in ("", "x", "15", "first three"):
            with self.subTest(answer=answer):
                code, out = self.batch("--select", answer)
                self.assertEqual(code, 3, out)
                self.assertRegex(out, r"^INVALID: .+\n$")
                self.assertNotIn("prompts:", out)
        self.assert_read_only()

    def test_an_answer_that_looks_like_a_flag_is_read_with_the_equals_form(self):
        code, out = self.batch("--select=-3")
        self.assertEqual(code, 3, out)
        self.assertRegex(out, r"^INVALID: ")
        self.assert_read_only()

    def test_it_needs_neither_the_effort_level_nor_a_usable_binary(self):
        env = {k: v for k, v in self.env.items() if k != "CLAUDE_EFFORT"}
        code, out = self.batch("--select", "2", env=env)
        self.assertEqual((code, out), (0, "prompts: game-lava-lamp\n"))
        self.assert_read_only()


class ListModeTest(BatchCase):
    def rows(self, out):
        return [m.groups() for m in re.finditer(r"(?m)^ ?(\d+)\. (\S+)  (.+)$", out)]

    def set_files(self, main_files=(), prs=()):
        st = self.git.state()
        st["main_files"] = list(main_files)
        st["prs"] = [{"number": n, "url": "https://example.test/pull/%d" % n, "files": [{"path": p}]}
                     for n, p in prs]
        self.git.save(st)

    def test_it_prints_a_header_and_fourteen_numbered_prompts_in_arm_order(self):
        code, out = self.batch("--list")
        self.assertEqual(code, 0, out)
        lines = out.splitlines()
        self.assertEqual(lines[0], "arm: 14 prompts for claude-fable-5-2 at effort high")
        self.assertEqual(len(lines), 15)
        self.assertEqual(self.rows(out), [(str(i), pid, "no result")
                                          for i, pid in enumerate(bra.ARM_PROMPTS, 1)])
        self.assertEqual(lines[1], " 1. game-melon-jelly  no result")
        self.assertEqual(lines[10], "10. game-weichensteller  no result")

    def test_a_result_on_origin_main_and_one_in_an_open_pr_are_marked(self):
        self.set_files(main_files=["results/lava-lamp/lava-lamp_claude_fable_5_2_high.html"],
                       prs=[(12, "results/minecraft/minecraft_claude_fable_5_2_high.html")])
        _, out = self.batch("--list")
        marks = {pid: mark for _, pid, mark in self.rows(out)}
        self.assertEqual(marks["game-lava-lamp"], "has result (on origin/main)")
        self.assertEqual(marks["game-minecraft"], "has result (open PR #12)")
        self.assertEqual(marks["game-melon-jelly"], "no result")
        self.assertIn(" 2. game-lava-lamp  has result (on origin/main)", out)
        self.assertIn(" 3. game-minecraft  has result (open PR #12)", out)

    def test_a_result_at_another_effort_or_for_another_model_shows_no_result(self):
        self.set_files(main_files=["results/melon-jelly/melon-jelly_claude_fable_5_2_max.html",
                                   "results/lava-lamp/lava-lamp_claude_opus_4_8_high.html"])
        _, out = self.batch("--list")
        self.assertEqual({m for _, _, m in self.rows(out)}, {"no result"})

    def test_only_fetch_ls_tree_and_gh_pr_list_run_and_nothing_is_created(self):
        code, out = self.batch("--list")
        self.assertEqual(code, 0, out)
        self.assertEqual([c[:3] for c in self.git.calls],
                         [["git", "fetch", "origin"], ["git", "ls-tree", "-r"], ["gh", "pr", "list"]])
        self.assertEqual(self.git.calls[0], ["git", "fetch", "origin", "main"])
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.repo / ".claude").exists())
        self.assertFalse(bra.lock_path(self.wt).exists())
        self.assertFalse((self.dir / "logs").exists())

    def test_it_does_not_run_the_binary_to_check_for_the_effort_flag(self):
        self.set_children(help_text="Usage: claude\n  --model <m>\n")
        code, out = self.batch("--list")
        self.assertEqual(code, 0, out)

    def test_a_missing_or_unknown_effort_or_an_alias_stops_before_any_git_call(self):
        no_effort = {k: v for k, v in self.env.items() if k != "CLAUDE_EFFORT"}
        for label, kw in (("unset", dict(env=no_effort)),
                          ("empty", dict(env=dict(self.env, CLAUDE_EFFORT=""))),
                          ("unknown", dict(env=dict(self.env, CLAUDE_EFFORT="ultra"))),
                          ("alias", dict(model="opus"))):
            with self.subTest(case=label):
                code, out = self.batch("--list", **kw)
                self.assertEqual(code, 2, out)
                self.assertRegex(out, r"(?m)^STOP: ")
                self.assertEqual(self.rows(out), [])
        self.assertEqual(self.git.calls, [])

    def test_a_failed_fetch_stops(self):
        def failing(cmd, **kw):
            if cmd[:2] == ["git", "fetch"]:
                return FakeGit.done(rc=1, err="fatal: no network\nmore")
            return self.git(cmd, **kw)
        code, out = self.batch("--list", runner=failing)
        self.assertEqual(code, 2)
        self.assertRegex(out, r"(?m)^STOP: .*fetch.*no network")
        self.assertEqual(self.rows(out), [])

    def test_a_failing_gh_pr_list_stops_instead_of_printing_a_misleading_list(self):
        def failing(cmd, **kw):
            if cmd[:3] == ["gh", "pr", "list"]:
                return FakeGit.done(rc=1, err="gh: not logged in")
            return self.git(cmd, **kw)
        code, out = self.batch("--list", runner=failing)
        self.assertEqual(code, 2)
        self.assertRegex(out, r"(?m)^STOP: .*gh pr list")
        self.assertEqual(self.rows(out), [])

    def test_a_broken_prompt_file_stops(self):
        (self.repo / "prompts" / "game-melon-jelly.toml").write_text("this is [not toml")
        code, out = self.batch("--list")
        self.assertEqual(code, 2, out)
        self.assertRegex(out, r"(?m)^STOP: ")
        self.assertEqual(self.git.calls, [])


class SubsetRunTest(BatchCase):
    CHOSEN = "game-minecraft,game-melon-jelly"

    def test_the_selected_prompts_run_in_arm_order_with_progress_within_the_selection(self):
        code, out = self.batch("--prompts", self.CHOSEN)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.called_ids(), ["game-melon-jelly", "game-minecraft"])
        self.assertIn("[1/2] game-melon-jelly  running ...", out)
        self.assertIn("[2/2] game-minecraft  pr-opened #2", out)
        self.assertNotIn("/14]", out)

    def test_the_report_lists_only_the_selected_prompts_and_counts_them(self):
        _, out = self.batch("--prompts", self.CHOSEN)
        self.assertEqual(list(self.report_lines(out)), ["game-melon-jelly", "game-minecraft"])
        self.assertRegex(out, r"(?m)^pr-opened: 2$")
        self.assertIn("\nreport: claude-fable-5-2 at effort high\n", out)

    def test_a_selected_prompt_that_already_has_a_result_is_skipped_and_reported(self):
        st = self.git.state()
        st["main_files"] = ["results/melon-jelly/melon-jelly_claude_fable_5_2_high.html"]
        self.git.save(st)
        code, out = self.batch("--prompts", self.CHOSEN)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.called_ids(), ["game-minecraft"])
        self.assertEqual(self.report_lines(out)["game-melon-jelly"][0], "skipped: on origin/main")
        self.assertIn("[1/2] game-melon-jelly  skipped: on origin/main", out)

    def test_an_unselected_prompt_with_a_result_is_not_mentioned(self):
        st = self.git.state()
        st["main_files"] = ["results/lava-lamp/lava-lamp_claude_fable_5_2_high.html"]
        self.git.save(st)
        _, out = self.batch("--prompts", self.CHOSEN)
        self.assertNotIn("game-lava-lamp", out)

    def test_the_merge_step_still_runs_after_a_subset(self):
        (self.repo / "harness").mkdir(exist_ok=True)
        (self.repo / "harness" / "merge_results.py").write_text(
            "import sys\nprint('merge args:', ' '.join(sys.argv[1:]))\n")
        code, out = self.batch("--prompts", "game-melon-jelly")
        self.assertRegex(out, r"(?m)^merge args: --model claude-fable-5-2 --post-statuses$")
        self.assertRegex(out, r"(?m)^merge step: ran harness/merge_results.py, exit 0$")
        self.assertEqual(code, 0)

    def test_prompts_all_is_the_whole_arm(self):
        code, out = self.batch("--prompts", "all")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.called_ids(), list(bra.ARM_PROMPTS))
        self.assertIn("[14/14] servicenow-loaner-request", out)

    def test_a_repeated_id_starts_one_child(self):
        self.batch("--prompts", "game-melon-jelly,game-melon-jelly")
        self.assertEqual(self.called_ids(), ["game-melon-jelly"])

    def test_after_a_halt_only_the_remaining_selected_prompts_are_not_started(self):
        self.set_children(by_prompt={"game-lava-lamp": {
            "effects": {"write": ["results/lava-lamp/stray.txt"]}}})
        code, out = self.batch("--prompts", "scene-sunset-ocean,game-melon-jelly,game-lava-lamp,game-minecraft")
        self.assertEqual(self.called_ids(), ["game-melon-jelly", "game-lava-lamp"])
        rep = self.report_lines(out)
        self.assertEqual(list(rep), ["game-melon-jelly", "game-lava-lamp", "game-minecraft", "scene-sunset-ocean"])
        self.assertEqual(rep["game-minecraft"][0], "not-started: tree dirty after game-lava-lamp")
        self.assertEqual(rep["scene-sunset-ocean"][0], "not-started: tree dirty after game-lava-lamp")
        self.assertRegex(out, r"(?m)^not-started: 2$")
        self.assertNotEqual(code, 0)

    def test_the_dry_run_shows_only_the_selected_prompts_and_creates_nothing(self):
        code, out = self.batch("--dry-run", "--prompts", "game-lava-lamp")
        self.assertEqual(code, 0, out)
        self.assertEqual(re.findall(r"(?m)^prompt .*$", out),
                         ["prompt game-lava-lamp: run  " + Path(self.targets["game-lava-lamp"]).name])
        self.assertEqual(out.count("child command:"), 1)
        self.assertIn("merge step: would list open PRs", out)
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.repo / ".claude").exists())

    def test_the_dry_run_marks_a_selected_prompt_that_would_be_skipped(self):
        st = self.git.state()
        st["main_files"] = ["results/lava-lamp/lava-lamp_claude_fable_5_2_high.html"]
        self.git.save(st)
        _, out = self.batch("--dry-run", "--prompts", "game-melon-jelly,game-lava-lamp")
        self.assertRegex(out, r"(?m)^prompt game-melon-jelly: run")
        self.assertRegex(out, r"(?m)^prompt game-lava-lamp: skip \(on origin/main\)")

    def test_the_dry_run_with_prompts_all_shows_the_whole_arm(self):
        _, out = self.batch("--dry-run", "--prompts", "all")
        self.assertEqual(len(re.findall(r"(?m)^prompt ", out)), 14)


class RejectedPromptsTest(BatchCase):
    def test_a_bad_value_stops_with_no_git_call_and_no_child_with_or_without_dry_run(self):
        for value in ("game-unknown", "", "a,,b", "3", "game-melon-jelly,", "game-melon-jelly,x", "ALL",
                      "all,game-melon-jelly"):
            for extra in ((), ("--dry-run",)):
                with self.subTest(value=value, extra=extra):
                    code, out = self.batch("--prompts", value, *extra)
                    self.assertEqual(code, 2, out)
                    self.assertRegex(out, r"(?m)^STOP: ")
                    self.assertEqual(self.git.calls, [])
                    self.assertEqual(self.calls(), [])
                    self.assertFalse((self.repo / ".claude").exists())

    def test_an_unknown_id_is_named_in_the_stop_line(self):
        _, out = self.batch("--prompts", "game-melon-jelly,game-unknown")
        self.assertIn("STOP: game-unknown is not one of the 14 arm prompts", out)

    def test_an_empty_value_does_not_quietly_mean_the_whole_arm(self):
        code, out = self.batch("--prompts", "")
        self.assertEqual(code, 2)
        self.assertEqual(self.calls(), [])

    def test_the_resolver_collapses_repeats_and_keeps_arm_order(self):
        self.assertEqual(bra.resolve_prompts("game-lava-lamp,game-melon-jelly,game-lava-lamp"),
                         arm(1, 2))
        self.assertEqual(bra.resolve_prompts(None), bra.ARM_PROMPTS)
        self.assertEqual(bra.resolve_prompts("all"), bra.ARM_PROMPTS)


class ModeConflictTest(unittest.TestCase):
    def parse(self, *argv):
        with contextlib.redirect_stderr(io.StringIO()):
            return bra.parse_args(["--model", "claude-fable-5-2", *argv])

    def test_list_select_and_smoke_exclude_each_other(self):
        for argv in (("--list", "--smoke", "x"), ("--select", "1", "--list"),
                     ("--select", "1", "--smoke", "x"), ("--smoke", "", "--list")):
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    self.parse(*argv)

    def test_prompts_cannot_be_combined_with_any_of_them(self):
        for argv in (("--prompts", "x", "--smoke", "y"), ("--prompts", "x", "--list"),
                     ("--prompts", "x", "--select", "1"), ("--prompts", "", "--list"),
                     ("--prompts", "x", "--smoke", "")):
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    self.parse(*argv)

    def test_an_empty_select_or_prompts_value_is_kept_as_given(self):
        self.assertEqual(self.parse("--select", "").select, "")
        self.assertEqual(self.parse("--prompts", "").prompts, "")
        args = self.parse()
        self.assertIsNone(args.select)
        self.assertIsNone(args.prompts)
        self.assertFalse(args.list)

    def test_dry_run_goes_with_prompts(self):
        args = self.parse("--dry-run", "--prompts", "game-melon-jelly")
        self.assertTrue(args.dry_run)
        self.assertEqual(args.prompts, "game-melon-jelly")


class BatchPreflightTest(BatchCase):
    def assert_no_child(self, code, out):
        self.assertEqual(code, 2)
        self.assertRegex(out, r"(?m)^STOP: ")
        self.assertEqual(self.calls(), [])

    def test_unset_effort_stops_before_any_child(self):
        env = {k: v for k, v in self.env.items() if k != "CLAUDE_EFFORT"}
        code, out = self.batch(env=env)
        self.assert_no_child(code, out)
        self.assertIn("CLAUDE_EFFORT", out)

    def test_empty_effort_stops_before_any_child(self):
        code, out = self.batch(env=dict(self.env, CLAUDE_EFFORT=""))
        self.assert_no_child(code, out)

    def test_unknown_effort_stops_before_any_child(self):
        code, out = self.batch(env=dict(self.env, CLAUDE_EFFORT="ultra"))
        self.assert_no_child(code, out)

    def test_binary_without_effort_flag_stops_before_any_child(self):
        self.set_children(help_text="Usage: claude\n  --model <m>\n")
        code, out = self.batch()
        self.assert_no_child(code, out)

    def test_alias_model_stops_before_any_child(self):
        code, out = self.batch(model="opus")
        self.assert_no_child(code, out)
        self.assertIn("alias", out)

    def test_not_on_main_stops_before_any_child(self):
        self.git.set_main(branch="feat/x")
        self.assert_no_child(*self.batch())

    def test_head_behind_origin_main_stops_before_any_child(self):
        self.git.set_shared(origin_main="def")
        self.assert_no_child(*self.batch())

    def test_untracked_files_in_the_main_checkout_do_not_stop_the_run(self):
        (self.repo / "results" / "x").mkdir(parents=True)
        (self.repo / "results" / "x" / "scratch.txt").write_text("x")
        (self.repo / "scratch.txt").write_text("x")
        code, out = self.batch()
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.calls()), 14)

    def test_modified_tracked_file_stops_before_any_child(self):
        self.git.set_main(dirty_tracked=["README.md"])
        self.assert_no_child(*self.batch())

    def test_gh_auth_failure_stops_before_any_child(self):
        st = self.git.state()
        st["gh_ok"] = False
        self.git.save(st)
        self.assert_no_child(*self.batch())


class BatchLoopTest(BatchCase):
    def test_a_clean_run_attempts_all_fourteen_in_order_and_reports_each_pr(self):
        code, out = self.batch()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.called_ids(), list(bra.ARM_PROMPTS))
        rep = self.report_lines(out)
        self.assertEqual(list(rep), list(bra.ARM_PROMPTS))
        self.assertEqual(rep["game-melon-jelly"], ("pr-opened #1", "https://example.test/pull/1"))
        self.assertEqual(rep["game-weichensteller"], ("pr-opened #10", "https://example.test/pull/10"))

    def test_every_child_gets_the_model_and_the_effort_level(self):
        self.batch()
        for call in self.calls():
            argv = call["argv"]
            self.assertEqual(argv[argv.index("--model") + 1], "claude-fable-5-2")
            self.assertEqual(argv[argv.index("--effort") + 1], "high")

    def test_progress_lines_come_before_the_report(self):
        _, out = self.batch()
        first_progress = out.index("[1/14] game-melon-jelly")
        self.assertLess(first_progress, out.index("game-melon-jelly  pr-opened"))

    def test_prompt_on_origin_main_is_skipped(self):
        st = self.git.state()
        st["main_files"] = ["results/melon-jelly/melon-jelly_claude_fable_5_2_high.html"]
        self.git.save(st)
        code, out = self.batch()
        self.assertNotIn("game-melon-jelly", self.called_ids())
        self.assertEqual(len(self.calls()), 13)
        self.assertEqual(self.report_lines(out)["game-melon-jelly"][0], "skipped: on origin/main")

    def test_a_result_at_another_effort_level_is_not_a_reason_to_skip(self):
        st = self.git.state()
        st["main_files"] = ["results/melon-jelly/melon-jelly_claude_fable_5_2_max.html"]
        self.git.save(st)
        _, out = self.batch()
        self.assertIn("game-melon-jelly", self.called_ids())
        self.assertEqual(len(self.calls()), 14)

    def test_the_report_names_the_model_and_the_effort_level(self):
        _, out = self.batch()
        self.assertIn("\nreport: claude-fable-5-2 at effort high\n", out)

    def test_prompt_in_an_open_pr_is_skipped_with_its_url(self):
        st = self.git.state()
        st["prs"] = [{"number": 42, "url": "https://example.test/pull/42", "files": [
            {"path": "results/lava-lamp/lava-lamp_claude_fable_5_2_high.html"}]}]
        st["next_pr"] = 43
        self.git.save(st)
        _, out = self.batch()
        self.assertNotIn("game-lava-lamp", self.called_ids())
        self.assertEqual(self.report_lines(out)["game-lava-lamp"],
                         ("skipped: open PR #42", "https://example.test/pull/42"))

    def test_a_result_for_another_model_does_not_skip(self):
        st = self.git.state()
        st["main_files"] = ["results/melon-jelly/melon-jelly_claude_opus_4_8.html"]
        self.git.save(st)
        self.batch()
        self.assertIn("game-melon-jelly", self.called_ids())

    def test_second_run_resumes_by_skipping_every_pr_the_first_opened(self):
        self.batch()
        before = len(self.calls())
        code, out = self.batch()
        self.assertEqual(len(self.calls()), before)
        rep = self.report_lines(out)
        self.assertTrue(all(o.startswith("skipped: open PR #") for o, _ in rep.values()), rep)
        self.assertEqual(code, 0)

    def test_failures_do_not_stop_the_batch(self):
        self.set_children(by_prompt={
            "game-melon-jelly": {"exit": 1, "effects": {}},
            "game-lava-lamp": {"sleep": 60, "effects": {}},
            "game-minecraft": {"json": result_json("STOP: results/x already exists on disk"), "effects": {}},
            "scene-meridian-launch": {"json": result_json("x\nrun void, re-run in a fresh session"),
                                     "effects": {}},
            "scene-sunset-ocean": {"json": result_json("x", is_error=True, subtype="error_during_execution"),
                                  "effects": {}},
        })
        # the 2 s timeout applies to every child; only lava-lamp is slow
        code, out = self.batch(timeout="2")
        self.assertEqual(self.called_ids(), list(bra.ARM_PROMPTS))
        rep = self.report_lines(out)
        self.assertEqual(rep["game-melon-jelly"][0], "failed: exit 1")
        self.assertEqual(rep["game-lava-lamp"][0], "timed-out")
        self.assertTrue(rep["game-minecraft"][0].startswith("ended without PR"))
        self.assertIn("STOP: results/x already exists on disk", rep["game-minecraft"][0])
        self.assertIn("run void", rep["scene-meridian-launch"][0])
        self.assertEqual(rep["scene-sunset-ocean"][0], "failed: error_during_execution")
        self.assertTrue(rep["game-horror-house"][0].startswith("pr-opened"))
        self.assertEqual(len(rep), 14)
        self.assertNotEqual(code, 0)

    def test_denied_tool_names_and_a_model_mismatch_are_reported_without_content(self):
        denial = [{"tool_name": "Read", "tool_input": {"file": "SECRET-DELIVERABLE"}}]
        self.set_children(by_prompt={"game-melon-jelly": {
            "json": result_json("SECRET-DELIVERABLE", permission_denials=denial,
                                modelUsage={"claude-opus-4-8": {}}),
            "effects": {"open_pr": True}}})
        _, out = self.batch()
        line = self.report_lines(out)["game-melon-jelly"][0]
        self.assertIn("denied: Read", line)
        self.assertIn("claude-opus-4-8", line)
        self.assertNotIn("SECRET", out)

    def test_counts_and_log_folder_are_reported(self):
        _, out = self.batch()
        self.assertRegex(out, r"(?m)^pr-opened: 14$")
        self.assertIn("log folder: %s" % (self.dir / "logs"), out)
        self.assertTrue((self.dir / "logs" / "game-melon-jelly.json").exists())

    def test_default_log_folder_is_outside_the_repo(self):
        with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": str(self.dir / "cache")}):
            folder = bra.make_log_dir(None)
        self.assertTrue(str(folder).startswith(str(self.dir / "cache" / "bench-run")))
        self.assertNotIn(self.repo, folder.parents)

    def test_default_log_folder_name_has_the_utc_stamp_and_the_run_tag(self):
        with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": str(self.dir / "cache")}):
            folder = bra.make_log_dir(None, "claude_fable_5_2_high")
        self.assertRegex(folder.name, r"^\d{8}T\d{6}Z_claude_fable_5_2_high$")

    def test_child_that_ends_without_a_pr_is_reported_as_such(self):
        self.set_children(by_prompt={"game-melon-jelly": {"effects": {}}})
        _, out = self.batch()
        self.assertEqual(self.report_lines(out)["game-melon-jelly"][0], "ended without PR")


class BatchCleanupTest(BatchCase):
    def test_own_untracked_leftovers_are_moved_to_the_log_folder_and_the_batch_continues(self):
        self.set_children(by_prompt={"game-melon-jelly": {
            "json": result_json("run void, re-run in a fresh session"),
            "effects": {"write": ["{target}"]}}})
        code, out = self.batch()
        self.assertEqual(len(self.calls()), 14)
        name = Path(self.targets["game-melon-jelly"]).name
        moved = self.dir / "logs" / "leftovers" / "game-melon-jelly" / name
        self.assertTrue(moved.is_file())
        self.assertEqual(moved.read_text(), "SECRET-DELIVERABLE")
        self.assertNotIn("SECRET", out)

    def test_a_clean_worktree_on_a_feature_branch_is_detached_at_origin_main_again(self):
        self.set_children(by_prompt={"game-melon-jelly": {"effects": {"branch": "feat/9-x"}}})
        self.batch()
        self.assertEqual(len(self.calls()), 14)
        self.assertEqual(self.calls()[0]["start_tree"]["branch"], "")
        self.assertEqual(self.calls()[1]["start_tree"]["branch"], "")  # after the feat/9-x child
        self.assertIn(["git", "switch", "--detach", "origin/main"], self.git.calls_in(self.wt))
        self.assertNotIn(["git", "switch", "main"], self.git.calls)

    def test_a_foreign_untracked_file_halts_the_batch_and_skips_the_merge_step(self):
        self.set_children(by_prompt={"game-lava-lamp": {
            "effects": {"write": ["results/lava-lamp/stray.txt"]}}})
        code, out = self.batch()
        self.assertEqual(self.called_ids(), ["game-melon-jelly", "game-lava-lamp"])
        rep = self.report_lines(out)
        self.assertEqual(rep["game-minecraft"][0], "not-started: tree dirty after game-lava-lamp")
        self.assertEqual(rep["game-weichensteller"][0], "not-started: tree dirty after game-lava-lamp")
        self.assertTrue((self.wt / "results/lava-lamp/stray.txt").exists())  # never touched
        self.assertIn("merge step: skipped", out)
        self.assertNotEqual(code, 0)

    def test_a_modified_tracked_file_halts_the_batch(self):
        self.set_children(by_prompt={"game-melon-jelly": {"effects": {"dirty_tracked": ["README.md"]}}})
        _, out = self.batch()
        self.assertEqual(self.called_ids(), ["game-melon-jelly"])
        self.assertIn("not-started: tree dirty after game-melon-jelly", out)

    def test_a_dirty_tree_on_another_branch_halts_instead_of_switching(self):
        self.set_children(by_prompt={"game-melon-jelly": {
            "effects": {"branch": "feat/9-x", "write": ["results/melon-jelly/stray.txt"]}}})
        self.batch()
        switches = [c for c in self.git.calls if c[:2] == ["git", "switch"]]
        self.assertEqual(switches, [["git", "switch", "--detach", "origin/main"]])  # setup's own
        self.assertEqual(self.called_ids(), ["game-melon-jelly"])


class WorktreeCreationTest(BatchCase):
    def test_a_worktree_is_added_detached_at_origin_main_from_the_repo(self):
        code, out = self.batch()
        self.assertEqual(code, 0, out)
        adds = [(c, w) for c, w in zip(self.git.calls, self.git.cwds) if c[:3] == ["git", "worktree", "add"]]
        self.assertEqual(adds, [(["git", "worktree", "add", "--detach", str(self.wt), "origin/main"],
                                 self.repo.resolve())])

    def test_every_child_runs_in_the_worktree_named_after_the_run_tag(self):
        self.batch()
        self.assertEqual(self.wt.name, "bench-run-claude_fable_5_2_high")
        self.assertEqual(len(self.calls()), 14)
        for call in self.calls():
            self.assertEqual(Path(call["cwd"]).resolve(), self.wt.resolve())

    def test_another_effort_level_gets_another_worktree(self):
        self.assertNotEqual(bra.worktree_path(self.repo, "claude-fable-5-2", "high"),
                            bra.worktree_path(self.repo, "claude-fable-5-2", "max"))
        self.assertNotEqual(bra.worktree_path(self.repo, "claude-fable-5-2", "high"),
                            bra.worktree_path(self.repo, "claude-opus-4-8", "high"))
        self.batch(env=dict(self.env, CLAUDE_EFFORT="max"))
        (add,) = [c for c in self.git.calls if c[:3] == ["git", "worktree", "add"]]
        self.assertEqual(add[4], str(self.wt_for("max")))

    def test_the_skip_check_and_snapshot_run_in_the_worktree(self):
        self.batch()
        self.assertIn(["git", "ls-tree", "-r", "--name-only", "origin/main", "--", "results/"],
                      self.git.calls_in(self.wt))


class MainCheckoutUntouchedTest(BatchCase):
    READ_ONLY_IN_REPO = (["git", "fetch"], ["git", "branch"], ["git", "rev-parse"], ["git", "status"],
                         ["git", "worktree"], ["gh", "auth"])

    def repo_files(self):
        return sorted(p.relative_to(self.repo).as_posix() for p in self.repo.rglob("*")
                      if p.is_file() and not p.relative_to(self.repo).as_posix().startswith(".claude/"))

    def test_branch_head_files_and_output_of_the_main_checkout_do_not_change(self):
        (self.repo / "scratch.txt").write_text("mine")
        before_tree, before_files = self.git.tree(), self.repo_files()
        self.set_children(by_prompt={
            "game-melon-jelly": {"effects": {"open_pr": True, "branch": "feat/9-x"}},
            "game-lava-lamp": {"effects": {"write": ["results/lava-lamp/stray.txt"]}}})
        self.batch()
        self.assertEqual(self.git.tree(), before_tree)
        self.assertEqual(self.repo_files(), before_files)
        self.assertTrue((self.wt / "results/lava-lamp/stray.txt").exists())
        self.assertFalse((self.repo / "results").exists())

    def test_only_read_only_git_runs_in_the_repo_besides_worktree_add_remove_prune(self):
        self.set_children(by_prompt={"game-melon-jelly": {"effects": {"branch": "feat/9-x"}}})
        self.batch()
        in_repo = self.git.calls_in(self.repo)
        self.assertTrue(in_repo)
        for cmd in in_repo:
            self.assertIn(cmd[:2], self.READ_ONLY_IN_REPO, cmd)
            if cmd[:2] == ["git", "worktree"]:
                self.assertIn(cmd[2], ("list", "add", "remove", "prune"))
            if cmd[:2] == ["git", "status"]:
                self.assertIn("--untracked-files=no", cmd)


class WorktreeLockTest(BatchCase):
    def hold(self, wt):
        wt.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(bra.lock_path(wt)), os.O_RDWR | os.O_CREAT, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX)
        self.addCleanup(os.close, fd)

    def test_a_second_run_for_the_same_model_and_effort_stops_with_a_stop_line(self):
        self.hold(self.wt)
        code, out = self.batch()
        self.assertEqual(code, 2)
        self.assertIn("STOP: worktree: %s is in use by another batch run for claude-fable-5-2 "
                      "at effort high" % self.wt, out)
        self.assertEqual(self.calls(), [])
        self.assertEqual([c for c in self.git.calls if c[:2] == ["git", "worktree"]], [])
        self.assertFalse(self.wt.exists())

    def test_dry_run_reports_the_same_in_use_state_as_a_failed_check(self):
        self.hold(self.wt)
        code, out = self.batch("--dry-run")
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"(?m)^check FAIL: worktree - .*in use")
        self.assertRegex(out, r"(?m)^STOP: worktree: .*in use")

    def test_a_lock_held_for_another_effort_level_does_not_block(self):
        self.hold(self.wt_for("max"))
        code, out = self.batch()
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.calls()), 14)

    def test_the_lock_fd_is_passed_to_every_child(self):
        with mock.patch.object(bra, "launch", wraps=bra.launch) as launch:
            self.batch()
        self.assertEqual(launch.call_count, 14)
        for call in launch.call_args_list:
            (fd,) = call.kwargs["pass_fds"]
            self.assertIsInstance(fd, int)


class LockTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.wt = Path(self.tmp.name) / ".claude" / "worktrees" / "bench-run-x"

    def test_the_lock_is_exclusive_until_the_holder_lets_go(self):
        first = bra.acquire_lock(self.wt)
        self.assertIsNotNone(first)
        self.assertIsNone(bra.acquire_lock(self.wt))
        self.assertTrue(bra.lock_in_use(self.wt))
        os.close(first)
        self.assertFalse(bra.lock_in_use(self.wt))
        again = bra.acquire_lock(self.wt)
        self.assertIsNotNone(again)
        os.close(again)

    def test_the_lock_file_survives_and_is_a_sibling_outside_the_worktree(self):
        os.close(bra.acquire_lock(self.wt))
        self.assertTrue(bra.lock_path(self.wt).is_file())
        self.assertEqual(bra.lock_path(self.wt).parent, self.wt.parent)
        self.assertFalse(self.wt.exists())

    def test_probing_never_creates_the_lock_or_its_folder(self):
        self.assertFalse(bra.lock_in_use(self.wt))
        self.assertFalse(self.wt.parent.exists())


class WorktreeReuseTest(BatchCase):
    def test_a_clean_worktree_left_on_a_feature_branch_is_reused_and_synced_first(self):
        self.git.register(self.wt, branch="feat/9-x", head="old")
        code, out = self.batch()
        self.assertEqual(code, 0, out)
        self.assertEqual([c for c in self.git.calls if c[:3] == ["git", "worktree", "add"]], [])
        first = self.calls()[0]["start_tree"]
        self.assertEqual((first["branch"], first["head"]), ("", "abc"))

    def test_a_clean_worktree_left_on_a_branch_at_an_unmerged_commit_is_still_reused(self):
        self.git.register(self.wt, branch="feat/9-x", head="child-commit")
        code, out = self.batch()
        self.assertEqual(code, 0, out)
        self.assertEqual([c for c in self.git.calls if c[:3] == ["git", "worktree", "add"]], [])
        self.assertEqual(self.calls()[0]["start_tree"]["head"], "abc")

    def test_a_clean_worktree_detached_at_an_unmerged_commit_stops_the_run_and_is_left_alone(self):
        self.git.register(self.wt, branch="", head="child-commit")
        code, out = self.batch()
        self.assertEqual(code, 2)
        self.assertRegex(out, r"(?m)^STOP: worktree: %s is detached at child-commit, which is not on "
                              r"origin/main; inspect it, put a branch on the commit to keep it, "
                              r"then git worktree remove %s$" % (re.escape(str(self.wt)), re.escape(str(self.wt))))
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.git.tree(self.wt), {"branch": "", "head": "child-commit", "dirty_tracked": []})
        self.assertTrue(self.wt.exists())
        touching = [c for c in self.git.calls
                    if c[:2] == ["git", "switch"] or (c[:2] == ["git", "worktree"] and c[2] in ("remove", "add", "prune"))]
        self.assertEqual(touching, [])

    def test_a_clean_worktree_detached_at_an_old_head_is_synced_to_origin_main(self):
        self.git.register(self.wt, branch="", head="old")
        self.batch()
        self.assertEqual(self.calls()[0]["start_tree"]["head"], "abc")

    def test_a_kept_dirty_worktree_stops_the_run_and_is_never_cleaned(self):
        self.git.register(self.wt)
        (self.wt / "results" / "x").mkdir(parents=True)
        (self.wt / "results" / "x" / "stray.txt").write_text("left over")
        code, out = self.batch()
        self.assertEqual(code, 2)
        self.assertIn("STOP: worktree: %s has 1 changed or untracked paths from an earlier run; "
                      "inspect it, then git worktree remove --force %s" % (self.wt, self.wt), out)
        self.assertEqual(self.calls(), [])
        self.assertTrue((self.wt / "results" / "x" / "stray.txt").exists())
        changing = [c for c in self.git.calls
                    if c[:2] == ["git", "worktree"] and c[2] in ("remove", "add", "prune")]
        self.assertEqual(changing, [])

    def test_a_tracked_change_in_a_kept_worktree_also_stops_the_run(self):
        self.git.register(self.wt, dirty_tracked=["README.md"])
        code, out = self.batch()
        self.assertEqual(code, 2)
        self.assertIn("has 1 changed or untracked paths", out)

    def test_a_folder_that_is_not_a_registered_worktree_stops_before_any_git_command_in_it(self):
        self.wt.mkdir(parents=True)
        (self.wt / "keep.txt").write_text("x")
        code, out = self.batch()
        self.assertEqual(code, 2)
        self.assertIn("STOP: worktree: %s exists but is not a worktree of this checkout; "
                      "remove it" % self.wt, out)
        self.assertEqual(self.git.calls_in(self.wt), [])
        self.assertEqual(self.calls(), [])
        self.assertEqual([c for c in self.git.calls if c[:2] == ["git", "switch"]], [])

    def test_a_registered_but_missing_worktree_is_pruned_then_added(self):
        self.git.register(self.wt)
        shutil.rmtree(self.wt)
        code, out = self.batch()
        self.assertEqual(code, 0, out)
        verbs = [c[2] for c in self.git.calls if c[:2] == ["git", "worktree"] and c[2] in ("prune", "add")]
        self.assertEqual(verbs, ["prune", "add"])


class WorktreeFinishTest(BatchCase):
    def remove_calls(self):
        return [(c, w) for c, w in zip(self.git.calls, self.git.cwds) if c[:3] == ["git", "worktree", "remove"]]

    def test_a_clean_finish_removes_the_worktree_without_force(self):
        code, out = self.batch()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.remove_calls(), [(["git", "worktree", "remove", str(self.wt)], self.repo.resolve())])
        self.assertIn("worktree: removed %s" % self.wt, out)
        self.assertLess(out.index("log folder:"), out.index("worktree: removed"))
        self.assertFalse(self.wt.exists())

    def test_failed_children_and_a_failed_merge_step_still_remove_the_worktree(self):
        (self.repo / "harness").mkdir(exist_ok=True)
        (self.repo / "harness" / "merge_results.py").write_text("import sys\nsys.exit(3)\n")
        self.set_children(by_prompt={"game-melon-jelly": {"exit": 1, "effects": {}}})
        code, out = self.batch()
        self.assertNotEqual(code, 0)
        self.assertEqual(len(self.remove_calls()), 1)
        self.assertIn("worktree: removed", out)
        self.assertFalse(self.wt.exists())

    def test_a_failed_removal_keeps_the_worktree_and_says_why_without_changing_the_exit_code(self):
        def flaky(cmd, **kw):
            if cmd[:3] == ["git", "worktree", "remove"]:
                self.git.calls.append(list(cmd))
                self.git.cwds.append(Path(kw["cwd"]).resolve())
                return FakeGit.done(rc=128, err="fatal: it is locked\nsecond line")
            return self.git(cmd, **kw)
        code, out = self.batch(runner=flaky)
        self.assertEqual(code, 0, out)
        self.assertIn("worktree: kept %s (git worktree remove failed: fatal: it is locked)" % self.wt, out)
        self.assertTrue(self.wt.exists())

    def test_a_halt_keeps_the_worktree_and_prints_its_path(self):
        self.set_children(by_prompt={"game-lava-lamp": {
            "effects": {"write": ["results/lava-lamp/stray.txt"]}}})
        code, out = self.batch()
        self.assertNotEqual(code, 0)
        self.assertEqual(self.remove_calls(), [])
        self.assertIn("worktree: kept %s (halted; the next run reuses it only if it is clean and on a branch or origin/main)" % self.wt, out)
        self.assertTrue((self.wt / "results/lava-lamp/stray.txt").exists())

    def test_the_run_after_a_halt_stops_on_the_dirty_worktree(self):
        self.set_children(by_prompt={"game-lava-lamp": {
            "effects": {"write": ["results/lava-lamp/stray.txt"]}}})
        self.batch()
        before = len(self.calls())
        code, out = self.batch()
        self.assertEqual(code, 2)
        self.assertEqual(len(self.calls()), before)
        self.assertRegex(out, r"(?m)^STOP: worktree: .*bench-run-claude_fable_5_2_high has 1 changed or untracked")


class WorktreeSettleTest(BatchCase):
    def test_a_child_that_moves_origin_main_is_followed_by_a_child_that_starts_there(self):
        self.set_children(by_prompt={"game-melon-jelly": {
            "effects": {"open_pr": True, "origin_main": "new1"}}})
        code, out = self.batch()
        self.assertEqual(code, 0, out)
        starts = [c["start_tree"] for c in self.calls()]
        self.assertEqual(starts[0]["head"], "abc")
        self.assertTrue(all(t["head"] == "new1" and t["branch"] == "" for t in starts[1:]))

    def test_a_child_that_commits_while_detached_halts_and_the_worktree_is_kept(self):
        self.set_children(by_prompt={"game-melon-jelly": {"effects": {"commit": True}}})
        code, out = self.batch()
        self.assertEqual(self.called_ids(), ["game-melon-jelly"])
        self.assertIn("not-started: HEAD moved without a branch after game-melon-jelly", out)
        self.assertIn("worktree: kept %s (halted" % self.wt, out)
        self.assertTrue(self.wt.exists())
        self.assertNotEqual(code, 0)

    def test_the_run_after_a_detached_commit_halt_stops_instead_of_dropping_the_commit(self):
        self.set_children(by_prompt={"game-melon-jelly": {"effects": {"commit": True}}})
        self.batch()
        before = len(self.calls())
        code, out = self.batch()
        self.assertEqual(code, 2)
        self.assertEqual(len(self.calls()), before)
        self.assertRegex(out, r"(?m)^STOP: worktree: .*bench-run-claude_fable_5_2_high is detached at child-commit")
        self.assertEqual(self.git.tree(self.wt)["head"], "child-commit")
        self.assertTrue(self.wt.exists())
        self.assertEqual([c for c in self.git.calls if c[:3] == ["git", "worktree", "remove"]], [])

    def test_a_failed_return_to_origin_main_halts(self):
        def failing(cmd, **kw):
            if cmd == ["git", "switch", "--detach", "origin/main"] and self.calls():
                self.git.calls.append(list(cmd))
                self.git.cwds.append(Path(kw["cwd"]).resolve())
                return FakeGit.done(rc=1, err="fatal: nope")
            return self.git(cmd, **kw)
        _, out = self.batch(runner=failing)
        self.assertEqual(self.called_ids(), ["game-melon-jelly"])
        self.assertIn("could not return to origin/main after game-melon-jelly", out)


class MergeStepTest(BatchCase):
    def add_merge_script(self, body):
        (self.repo / "harness").mkdir(exist_ok=True)
        (self.repo / "harness" / "merge_results.py").write_text(body)

    def test_existing_merge_script_runs_with_the_model_and_its_output_is_passed_through(self):
        self.add_merge_script(
            "import sys\nprint('merge args:', ' '.join(sys.argv[1:]))\nsys.exit(0)\n")
        code, out = self.batch()
        self.assertRegex(out, r"(?m)^merge args: --model claude-fable-5-2 --post-statuses$")
        self.assertRegex(out, r"(?m)^merge step: ran harness/merge_results.py, exit 0$")
        self.assertEqual(code, 0)

    def test_merge_script_exit_code_is_recorded_and_fails_the_run(self):
        self.add_merge_script("import sys\nprint('refusing')\nsys.exit(3)\n")
        code, out = self.batch()
        self.assertRegex(out, r"(?m)^merge step: ran harness/merge_results.py, exit 3$")
        self.assertNotEqual(code, 0)

    def test_without_the_script_open_prs_touching_the_arm_files_are_listed(self):
        st = self.git.state()
        st["prs"] = [{"number": 5, "url": "https://example.test/pull/5", "files": [
            {"path": "results/other/other_claude_opus_4_8.html"}]}]
        st["next_pr"] = 6
        self.git.save(st)
        code, out = self.batch()
        self.assertIn("merge step: harness/merge_results.py not present; open PRs for this arm:", out)
        self.assertIn("https://example.test/pull/6", out)
        self.assertNotIn("https://example.test/pull/5", out)
        self.assertEqual(code, 0)

    def test_merge_script_runs_after_cleanup_returned_to_origin_main(self):
        self.add_merge_script("print('MERGE-RAN')\n")
        self.set_children(by_prompt={"game-weichensteller": {
            "effects": {"open_pr": True, "branch": "feat/z"}}})
        _, out = self.batch()
        self.assertIn("MERGE-RAN", out)

    def test_merge_script_is_not_run_when_the_tree_is_dirty(self):
        self.add_merge_script("print('MERGE-RAN')\n")
        self.set_children(by_prompt={"game-weichensteller": {
            "effects": {"open_pr": True, "write": ["results/x/stray.txt"]}}})
        _, out = self.batch()
        self.assertNotIn("MERGE-RAN", out)
        self.assertIn("merge step: skipped", out)

    def test_skip_everything_still_reaches_the_merge_step(self):
        self.batch()
        self.add_merge_script("print('MERGED')\n")
        before = len(self.calls())
        _, out = self.batch()
        self.assertEqual(len(self.calls()), before)
        self.assertIn("MERGED", out)


class RunMetricsBatchTest(BatchCase):
    """The step after each child that opened a PR: run file by contents API, then the description."""

    SIX = ["duration_seconds", "input_tokens", "output_tokens",
           "cache_read_tokens", "cache_write_tokens", "cost_usd"]

    def puts(self):
        return self.git.state()["puts"]

    def edits(self):
        return self.git.state()["edits"]

    def metrics_calls(self):
        return [c for c in self.git.calls
                if c[:3] in (["gh", "pr", "view"], ["gh", "pr", "edit"]) or c[:2] == ["gh", "api"]]

    def run_one(self, pid="game-melon-jelly", **kw):
        return self.batch("--prompts", pid, **kw)

    def one_note(self, out, pid="game-melon-jelly"):
        return self.report_lines(out)[pid][0]

    def test_each_opened_pr_gets_one_run_file_commit_on_its_own_branch(self):
        self.batch()
        puts = self.puts()
        self.assertEqual(len(puts), 14)
        prs = self.git.state()["prs"]
        for pid, put in zip(bra.ARM_PROMPTS, puts):
            target = self.targets[pid]
            self.assertEqual(put["path"], target.rsplit(".", 1)[0] + ".run.json")
            (own,) = [p for p in prs if target in [f["path"] for f in p["files"]]]
            self.assertEqual(put["branch"], own["headRefName"])
            prefix = bra._prompt_data(self.repo, pid)["file_prefix"]
            self.assertEqual(put["message"],
                             "feat(results): add %s claude-fable-5-2 high run metrics" % prefix)

    def test_the_run_file_holds_exactly_the_six_keys_in_contract_order(self):
        self.run_one()
        (put,) = self.puts()
        self.assertTrue(put["content"].endswith("\n"))
        data = json.loads(put["content"])
        self.assertEqual(list(data), self.SIX)
        self.assertEqual(data, {"duration_seconds": 821.3, "input_tokens": 28, "output_tokens": 77902,
                                "cache_read_tokens": 1082945, "cache_write_tokens": 109699,
                                "cost_usd": 5.088077})
        self.assertEqual(put["content"], json.dumps(data, indent=2) + "\n")

    def test_the_description_gets_the_section_before_the_closes_line(self):
        self.run_one()
        (edit,) = self.edits()
        body = edit["body"]
        self.assertEqual(body.count("<!-- run-metrics -->"), 1)
        for text in ("Duration 821.3 s", "77,902 output tokens", "5.088077 USD", "| Input | 28 |",
                     "| Cache read | 1,082,945 |", "| Cache write | 109,699 |",
                     "melon-jelly_claude_fable_5_2_high.run.json"):
            self.assertIn(text, body)
        self.assertLess(body.index("<!-- /run-metrics -->"), body.index("Closes #%d" % edit["number"]))
        self.assertTrue(body.startswith("## Summary\n\ntext\n\n"))

    def test_success_adds_no_note_to_the_report_line(self):
        _, out = self.batch()
        rep = self.report_lines(out)
        for pid in bra.ARM_PROMPTS:
            self.assertRegex(rep[pid][0], r"^pr-opened #\d+$")

    def test_only_the_run_file_is_added_to_the_pr(self):
        self.run_one()
        (put,) = self.puts()
        files = [f["path"] for f in self.git.state()["prs"][0]["files"]]
        self.assertEqual(files, [self.targets["game-melon-jelly"], put["path"]])

    def test_without_usable_usage_no_run_file_is_written_and_the_description_says_so(self):
        zero = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0}
        self.set_children(default={"json": result_json("done", usage=zero, total_cost_usd=0)})
        _, out = self.batch()
        self.assertEqual(self.puts(), [])
        self.assertEqual(len(self.calls()), 14)
        self.assertEqual(len(self.edits()), 14)
        for edit in self.edits():
            self.assertIn("Unavailable: the JSON output of the batch session", edit["body"])
            self.assertNotIn("| Input |", edit["body"])
        rep = self.report_lines(out)
        for pid in bra.ARM_PROMPTS:
            self.assertRegex(rep[pid][0], r"^pr-opened #\d+ \(run metrics unavailable\)$")

    def test_a_failed_description_edit_without_usage_is_reported_and_the_batch_goes_on(self):
        self.set_children(default={"json": result_json("done", usage=None)})
        self.git.set_shared(gh_fail={"edit": "HTTP 502: bad gateway\nsecond line\n"})
        _, out = self.batch()
        self.assertEqual(len(self.calls()), 14)
        self.assertEqual(self.one_note(out), "pr-opened #1 (run metrics unavailable, "
                                             "PR description not updated: HTTP 502: bad gateway)")

    def test_a_failed_put_leaves_the_pr_alone_says_so_and_the_batch_continues(self):
        clean_code, _ = self.batch()
        self.setUp()
        self.git.set_shared(gh_fail={"put": "HTTP 422: Validation Failed\nsecond line SECRET\n"})
        code, out = self.batch()
        self.assertEqual(code, clean_code)
        self.assertEqual(self.called_ids(), list(bra.ARM_PROMPTS))
        self.assertEqual(self.puts(), [])
        self.assertEqual(self.edits(), [])
        self.assertEqual([c for c in self.git.calls if c[:3] == ["gh", "pr", "edit"]], [])
        rep = self.report_lines(out)
        for pid in bra.ARM_PROMPTS:
            self.assertRegex(rep[pid][0],
                             r"^pr-opened #\d+ \(run file not added: HTTP 422: Validation Failed\)$")
        self.assertNotIn("SECRET", out)
        self.assertIn("worktree: removed", out)

    def test_a_failed_put_does_not_stop_the_merge_step(self):
        (self.repo / "harness").mkdir(exist_ok=True)
        (self.repo / "harness" / "merge_results.py").write_text("print('MERGE-RAN')\n")
        self.git.set_shared(gh_fail={"put": "HTTP 500: boom"})
        code, out = self.batch()
        self.assertIn("MERGE-RAN", out)
        self.assertEqual(code, 0)

    def test_a_failed_edit_after_the_put_keeps_the_run_file_and_says_so(self):
        self.git.set_shared(gh_fail={"edit": "HTTP 403: nope\nmore"})
        _, out = self.run_one()
        self.assertEqual(len(self.puts()), 1)
        self.assertEqual(self.edits(), [])
        self.assertEqual(self.one_note(out),
                         "pr-opened #1 (run file added, PR description not updated: HTTP 403: nope)")

    def test_a_long_reason_is_capped_and_has_no_double_space(self):
        self.git.set_shared(gh_fail={"put": "HTTP 422: " + "word  " * 100})
        _, out = self.run_one()
        note = self.one_note(out)
        self.assertNotIn("  ", note)
        self.assertLessEqual(len(note), len("pr-opened #1 (run file not added: )") + 200)
        self.assertIn("pr-opened #1 (run file not added: HTTP 422: word word", note)

    def test_a_failed_pr_read_changes_nothing(self):
        self.git.set_shared(gh_fail={"view": "HTTP 404: gone"})
        _, out = self.run_one()
        self.assertEqual((self.puts(), self.edits()), ([], []))
        self.assertEqual(self.one_note(out), "pr-opened #1 (run file not added: HTTP 404: gone)")

    def test_a_failed_pr_read_without_usage_says_both(self):
        self.set_children(default={"json": result_json("done", usage=None)})
        self.git.set_shared(gh_fail={"view": "HTTP 404: gone"})
        _, out = self.run_one()
        self.assertEqual((self.puts(), self.edits()), ([], []))
        self.assertEqual(self.one_note(out), "pr-opened #1 (run metrics unavailable, "
                                             "PR description not updated: HTTP 404: gone)")

    def test_a_pr_that_is_not_this_results_pr_gets_no_write(self):
        target = self.targets["game-melon-jelly"]
        run_file = target.rsplit(".", 1)[0] + ".run.json"
        other_branch = "feat/1-melon-jelly-claude-fable-5-2-max-result"
        cases = {
            "not open": ({"state": "CLOSED"}, "PR #1 is not open"),
            "merged": ({"state": "MERGED"}, "PR #1 is not open"),
            "from a fork": ({"isCrossRepository": True}, "PR #1 comes from a fork"),
            "other branch": ({"headRefName": "feat/9-x"}, "branch feat/9-x is not this result's branch"),
            "other effort": ({"headRefName": other_branch},
                             "branch %s is not this result's branch" % other_branch),
            "run file already there": ({"files": [{"path": target}, {"path": run_file}]},
                                       "PR #1 already has the run file"),
            "two deliverables": ({"files": [{"path": target},
                                            {"path": target.replace("melon-jelly/", "other/")}]},
                                 "PR #1 does not have exactly one deliverable"),
            "odd path": ({"files": [{"path": "results/a b/" + Path(target).name}]},
                         "PR #1 does not have exactly one deliverable"),
        }
        for label, (extra, reason) in cases.items():
            with self.subTest(label):
                self.setUp()
                self.set_children(by_prompt={"game-melon-jelly": {
                    "effects": {"open_pr": True, "pr_extra": extra}}})
                _, out = self.run_one()
                self.assertEqual((self.puts(), self.edits()), ([], []))
                self.assertEqual([c for c in self.git.calls if c[:2] == ["gh", "api"]], [])
                self.assertEqual(self.one_note(out), "pr-opened #1 (run file not added: %s)" % reason)

    def test_skipped_prompts_run_no_metrics_step(self):
        st = self.git.state()
        st["main_files"] = [Path(self.targets["game-melon-jelly"]).as_posix()]
        st["prs"] = [{"number": 42, "url": "https://example.test/pull/42", "files": [
            {"path": self.targets["game-lava-lamp"]}]}]
        st["next_pr"] = 43
        self.git.save(st)
        self.batch("--prompts", "game-melon-jelly,game-lava-lamp")
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.metrics_calls(), [])

    def test_failed_and_ended_without_pr_prompts_run_no_metrics_step(self):
        self.set_children(by_prompt={"game-melon-jelly": {"exit": 1, "effects": {}},
                                     "game-lava-lamp": {"effects": {}}})
        self.batch("--prompts", "game-melon-jelly,game-lava-lamp")
        self.assertEqual(self.metrics_calls(), [])

    def test_a_timed_out_child_without_a_pr_runs_no_metrics_step(self):
        self.set_children(by_prompt={"game-melon-jelly": {"sleep": 60, "effects": {}}})
        _, out = self.run_one(timeout="1")
        self.assertEqual(self.metrics_calls(), [])
        self.assertEqual(self.one_note(out), "timed-out")

    def test_a_child_that_opened_a_pr_and_then_timed_out_gets_the_unavailable_section_only(self):
        self.set_children(by_prompt={"game-melon-jelly": {"sleep": 60, "json": result_json("x")}})
        _, out = self.run_one(timeout="2")
        self.assertEqual(self.puts(), [])
        (edit,) = self.edits()
        self.assertIn("Unavailable:", edit["body"])
        self.assertEqual(self.one_note(out), "pr-opened #1 (run metrics unavailable)")

    def test_the_step_runs_no_git_command_that_moves_the_worktree(self):
        _, out = self.batch()
        git_cmds = [c for c in self.git.calls if c[0] == "git"]
        for sub in ("add", "commit", "push", "checkout", "reset", "stash"):
            self.assertEqual([c for c in git_cmds if c[1] == sub], [])
        self.assertEqual([c for c in git_cmds if c[1] == "switch" and c[2:] != ["--detach", "origin/main"]], [])
        self.assertIn("worktree: removed", out)

    def test_the_metrics_gh_calls_run_in_the_worktree_and_never_merge(self):
        self.run_one()
        views = [w for c, w in zip(self.git.calls, self.git.cwds) if c[:3] == ["gh", "pr", "view"]]
        self.assertEqual(views, [self.wt.resolve()])
        for cmd in self.git.calls:
            self.assertNotEqual(cmd[:3], ["gh", "pr", "merge"])
        api = [c for c in self.git.calls if c[:2] == ["gh", "api"]]
        self.assertEqual(len(api), 1)
        self.assertEqual(api[0][2:4], ["--method", "PUT"])
        self.assertIn("-f", api[0])

    def test_no_result_text_pr_body_or_run_content_reaches_the_output(self):
        _, out = self.batch()
        self.assertNotIn("SECRET", out)
        for text in ("## Run metrics", "Closes #", "run-metrics", "77,902", "5.088077"):
            self.assertNotIn(text, out)

    def test_secret_text_never_lands_in_the_run_file_or_the_description(self):
        denial = [{"tool_name": "Read", "tool_input": {"x": "SECRET"}}]
        self.set_children(default={"json": result_json("SECRET-DELIVERABLE", permission_denials=denial)})
        self.batch()
        self.assertEqual(len(self.puts()), 14)
        for put in self.puts():
            self.assertNotIn("SECRET", put["content"] + put["message"])
        for edit in self.edits():
            self.assertNotIn("SECRET", edit["body"])

    def test_a_second_run_skips_every_pr_and_touches_none(self):
        self.batch()
        before = (len(self.puts()), len(self.edits()), len(self.metrics_calls()))
        self.batch()
        self.assertEqual((len(self.puts()), len(self.edits()), len(self.metrics_calls())), before)

    def test_the_description_file_lives_in_the_log_folder_not_the_worktree(self):
        paths = []
        original = self.git.pr_edit

        def spy(cmd, st):
            paths.append(Path(cmd[5]))
            return original(cmd, st)

        self.git.pr_edit = spy
        self.run_one()
        (path,) = paths
        self.assertEqual(path.parent, self.dir / "logs")
        self.assertTrue(path.name.endswith(".pr-body.md"))


class DryRunTest(BatchCase):
    def test_dry_run_starts_no_child_and_names_every_prompt_and_file(self):
        code, out = self.batch("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.calls(), [])  # the fake logs real children only, not --help
        for pid in bra.ARM_PROMPTS:
            self.assertIn(pid, out)
            self.assertIn(Path(self.targets[pid]).name, out)

    def test_dry_run_issues_only_read_only_git_and_gh_commands(self):
        self.batch("--dry-run")
        for cmd in self.git.calls:
            self.assertIn(cmd[:2], (["git", "fetch"], ["git", "branch"], ["git", "rev-parse"],
                                    ["git", "status"], ["git", "ls-tree"], ["gh", "auth"],
                                    ["gh", "pr"], ["git", "worktree"]), cmd)
            if cmd[:2] == ["git", "worktree"]:
                self.assertEqual(cmd[:3], ["git", "worktree", "list"])
        self.assertEqual([c for c in self.git.calls if c[:2] == ["git", "switch"]], [])

    def test_dry_run_shows_run_and_skip_per_prompt(self):
        st = self.git.state()
        st["main_files"] = ["results/melon-jelly/melon-jelly_claude_fable_5_2_high.html"]
        self.git.save(st)
        _, out = self.batch("--dry-run")
        self.assertRegex(out, r"(?m)^prompt game-melon-jelly: skip \(on origin/main\)")
        self.assertRegex(out, r"(?m)^prompt game-lava-lamp: run")

    def test_dry_run_shows_the_exact_child_command_once(self):
        _, out = self.batch("--dry-run")
        self.assertEqual(out.count("child command:"), 1)
        line = [ln for ln in out.splitlines() if ln.startswith("child command:")][0]
        self.assertIn("--model claude-fable-5-2", line)
        self.assertIn("--effort high", line)
        self.assertIn("--permission-mode dontAsk", line)

    def test_dry_run_names_the_final_branch(self):
        _, out = self.batch("--dry-run")
        self.assertIn("merge step: would list open PRs", out)
        (self.repo / "harness").mkdir(exist_ok=True)
        (self.repo / "harness" / "merge_results.py").write_text("")
        _, out = self.batch("--dry-run")
        self.assertRegex(out, r"(?m)^merge step: would run python3 harness/merge_results.py "
                              r"--model claude-fable-5-2 --post-statuses$")

    def test_dry_run_shows_checks_as_ok_or_fail_and_exits_nonzero_on_failure(self):
        code, out = self.batch("--dry-run")
        self.assertRegex(out, r"(?m)^check ok: effort")
        self.git.set_main(dirty_tracked=["README.md"])
        code, out = self.batch("--dry-run")
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"(?m)^check FAIL: no tracked changes")
        self.assertEqual(self.calls(), [])

    def test_dry_run_creates_no_worktree_folder_or_lock_and_says_where_one_would_go(self):
        code, out = self.batch("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"(?m)^check ok: worktree - would create %s$" % re.escape(str(self.wt)))
        self.assertFalse((self.repo / ".claude").exists())

    def test_dry_run_says_would_reuse_for_a_clean_kept_worktree_and_changes_nothing(self):
        self.git.register(self.wt, branch="feat/9-x", head="old")
        code, out = self.batch("--dry-run")
        self.assertRegex(out, r"(?m)^check ok: worktree - would reuse ")
        self.assertEqual(self.git.tree(self.wt), {"branch": "feat/9-x", "head": "old", "dirty_tracked": []})
        self.assertFalse(bra.lock_path(self.wt).exists())

    def test_dry_run_fails_the_worktree_check_for_a_worktree_detached_at_an_unmerged_commit(self):
        self.git.register(self.wt, branch="", head="child-commit")
        code, out = self.batch("--dry-run")
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"(?m)^check FAIL: worktree - .* is detached at child-commit, which is not on origin/main")
        self.assertEqual(self.git.tree(self.wt), {"branch": "", "head": "child-commit", "dirty_tracked": []})

    def test_dry_run_says_would_reuse_for_a_branch_at_an_unmerged_commit(self):
        self.git.register(self.wt, branch="feat/9-x", head="child-commit")
        _, out = self.batch("--dry-run")
        self.assertRegex(out, r"(?m)^check ok: worktree - would reuse ")

    def test_dry_run_says_would_prune_and_create_for_a_registered_missing_worktree(self):
        self.git.register(self.wt)
        shutil.rmtree(self.wt)
        _, out = self.batch("--dry-run")
        self.assertRegex(out, r"(?m)^check ok: worktree - would prune and create ")

    def test_dry_run_fails_the_worktree_check_for_a_dirty_kept_worktree(self):
        self.git.register(self.wt, dirty_tracked=["README.md"])
        code, out = self.batch("--dry-run")
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"(?m)^check FAIL: worktree - .*has 1 changed or untracked paths")

    def test_dry_run_prints_the_stop_line_for_a_missing_effort(self):
        env = {k: v for k, v in self.env.items() if k != "CLAUDE_EFFORT"}
        code, out = self.batch("--dry-run", env=env)
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"(?m)^STOP: .*CLAUDE_EFFORT")


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class RealGitWorktreeTest(unittest.TestCase):
    """The worktree helpers against real git, with ``_run`` unpatched.

    The fake cannot catch a mistake in ``git worktree list --porcelain``
    parsing or in what ``worktree remove`` refuses; a throwaway repo with a
    local bare ``origin`` does.
    """

    def git(self, *cmd, cwd=None):
        done = subprocess.run(["git", *cmd], cwd=cwd or self.repo, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        env = {"HOME": str(root), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.test",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.test"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.origin, self.repo = root / "origin.git", root / "repo"
        self.git("init", "-q", "--bare", "-b", "main", str(self.origin), cwd=root)
        self.git("init", "-q", "-b", "main", str(self.repo), cwd=root)
        (self.repo / ".gitignore").write_text(".claude/worktrees/\n.bench-run/\n")
        (self.repo / "README.md").write_text("x\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "init")
        self.git("remote", "add", "origin", str(self.origin))
        self.git("push", "-q", "origin", "main")
        self.git("fetch", "-q", "origin", "main")
        self.wt = bra.worktree_path(self.repo, "claude-fable-5-2", "high")

    def test_setup_creates_a_detached_worktree_at_origin_main(self):
        self.assertEqual(bra.classify_worktree(self.repo, self.wt), "create")
        self.assertEqual(bra.setup_worktree(self.repo, self.wt), "create")
        self.assertEqual(self.git("branch", "--show-current", cwd=self.wt), "")
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.wt), self.git("rev-parse", "origin/main"))
        self.assertEqual(self.git("status", "--porcelain", cwd=self.repo), "")  # main checkout untouched
        self.assertEqual(self.git("branch", "--show-current"), "main")

    def test_a_created_worktree_is_found_again_in_the_porcelain_listing(self):
        bra.setup_worktree(self.repo, self.wt)
        self.assertEqual(bra.classify_worktree(self.repo, self.wt), "reuse")
        self.assertEqual(bra.setup_worktree(self.repo, self.wt), "reuse")

    def test_a_reused_worktree_on_a_feature_branch_is_synced_back(self):
        bra.setup_worktree(self.repo, self.wt)
        self.git("switch", "-q", "-c", "feat/1-x", cwd=self.wt)
        (self.wt / "new.txt").write_text("y")
        self.git("add", "new.txt", cwd=self.wt)
        self.git("commit", "-q", "-m", "child", cwd=self.wt)
        self.assertIsNone(bra.sync_worktree(self.wt))
        self.assertEqual(self.git("branch", "--show-current", cwd=self.wt), "")
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.wt), self.git("rev-parse", "origin/main"))
        self.assertTrue(self.git("branch", "--list", "feat/1-x"))  # the child's commit stays reachable

    def test_a_detached_commit_not_on_origin_main_is_a_stop_but_a_branch_on_it_is_reusable(self):
        bra.setup_worktree(self.repo, self.wt)
        self.git("commit", "-q", "--allow-empty", "-m", "child", cwd=self.wt)
        sha = self.git("rev-parse", "HEAD", cwd=self.wt)
        with self.assertRaises(bra.WorktreeStop) as ctx:
            bra.classify_worktree(self.repo, self.wt)
        self.assertIn(str(self.wt), str(ctx.exception))
        self.assertIn(sha, str(ctx.exception))
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.wt), sha)
        self.git("switch", "-q", "-c", "feat/1-x", cwd=self.wt)
        self.assertEqual(bra.setup_worktree(self.repo, self.wt), "reuse")
        self.assertTrue(self.git("branch", "--list", "feat/1-x"))

    def test_remove_succeeds_with_only_ignored_files_and_is_refused_for_untracked_results(self):
        bra.setup_worktree(self.repo, self.wt)
        (self.wt / ".bench-run").mkdir()
        (self.wt / ".bench-run" / "x.pr.md").write_text("body")
        (self.wt / "results").mkdir()
        (self.wt / "results" / "stray.txt").write_text("y")
        kept = bra.finish_worktree(self.repo, self.wt, halt=None)
        self.assertIn("worktree: kept %s (git worktree remove failed:" % self.wt, kept)
        self.assertTrue(self.wt.exists())
        (self.wt / "results" / "stray.txt").unlink()
        self.assertEqual(bra.finish_worktree(self.repo, self.wt, halt=None),
                         "worktree: removed %s" % self.wt)
        self.assertFalse(self.wt.exists())

    def test_a_registered_but_deleted_worktree_is_pruned_and_created_again(self):
        bra.setup_worktree(self.repo, self.wt)
        shutil.rmtree(self.wt)
        self.assertEqual(bra.classify_worktree(self.repo, self.wt), "prune and create")
        self.assertEqual(bra.setup_worktree(self.repo, self.wt), "prune and create")
        self.assertEqual(bra.classify_worktree(self.repo, self.wt), "reuse")

    def test_a_plain_folder_is_not_taken_for_a_worktree_and_git_never_runs_in_it(self):
        self.wt.mkdir(parents=True)
        with self.assertRaises(bra.WorktreeStop) as ctx:
            bra.setup_worktree(self.repo, self.wt)
        self.assertIn("not a worktree of this checkout", str(ctx.exception))
        self.assertEqual(self.git("branch", "--show-current"), "main")

    def test_a_dirty_kept_worktree_is_a_stop_that_names_the_path(self):
        bra.setup_worktree(self.repo, self.wt)
        (self.wt / "stray.txt").write_text("y")
        with self.assertRaises(bra.WorktreeStop) as ctx:
            bra.setup_worktree(self.repo, self.wt)
        self.assertIn(str(self.wt), str(ctx.exception))
        self.assertIn("1 changed or untracked paths", str(ctx.exception))


BENCH_RUN_MODES = ("plan", "meta", "prompt", "issue-body", "pr-body")


def rule_matches(rule, command):
    """Whether a ``Bash(...)`` allow rule's literal prefix admits ``command``.

    A trailing ``*`` is a plain string-prefix match (the space before it forces
    a word boundary); a rule without one matches the exact command only.
    """
    inner = rule[len("Bash("):-1]
    if inner.endswith("*"):
        return command.startswith(inner[:-1])
    return command == inner


def skill_steps():
    text = (REPO / ".claude" / "skills" / "bench-run" / "SKILL.md").read_text(encoding="utf-8")
    return text.split("\n## Steps\n", 1)[1].split("\n## Naming\n", 1)[0]


# Documented interactive-only commands: a batch child never needs them.
INTERACTIVE_ONLY = ("python3 harness/bench_run.py grade ", "git restore ")


def skill_text():
    return (REPO / ".claude" / "skills" / "bench-run" / "SKILL.md").read_text(encoding="utf-8")


def batch_mode():
    return skill_text().split("## Batch mode\n", 1)[1].split("\n## One-shot rules\n", 1)[0]


def batch_helper_commands():
    """argv (after the script name) of every helper command in Batch mode, placeholders filled in."""
    import shlex
    fills = {"<model-id>": "claude-fable-5-2", "<selection>": "game-melon-jelly,game-lava-lamp",
             "<answer>": "1,3-5"}
    found = []
    for span in re.findall(r"`(python3 harness/bench_run_all\.py [^`\n]+)`", batch_mode()):
        for placeholder, value in fills.items():
            span = span.replace(placeholder, value)
        assert "<" not in span, span
        found.append(shlex.split(span)[2:])
    return found


def step_commands():
    """Every inline-code span in the Steps that is a shell command."""
    spans = re.findall(r"`([^`\n]+)`", skill_steps())
    return [c for c in spans if re.match(r"(git|gh|python3?) ", c)]


class AllowlistTest(unittest.TestCase):
    def test_no_inline_python_rule_remains(self):
        self.assertEqual([r for r in bra.ALLOWED_TOOLS
                          if r.startswith(("Bash(python3 -", "Bash(python -"))], [])

    def test_exactly_the_five_bench_run_modes_are_allowed_as_script_rules(self):
        scripts = [r for r in bra.ALLOWED_TOOLS if "python" in r]
        self.assertEqual(scripts, ["Bash(python3 harness/bench_run.py %s *)" % m
                                   for m in BENCH_RUN_MODES])

    def test_a_child_cannot_start_the_batch_helper_or_grade(self):
        for banned in ("python3 harness/bench_run_all.py --model x",
                       "python3 harness/bench_run.py grade game-melon-jelly claude-fable-5-2",
                       "python3 harness/merge_results.py --model x",
                       "python3 -c print(1)", "python3 - game-melon-jelly"):
            with self.subTest(command=banned):
                self.assertFalse([r for r in bra.ALLOWED_TOOLS
                                  if r.startswith("Bash(") and rule_matches(r, banned)])

    def test_the_rule_for_a_mode_does_not_admit_a_longer_mode_name(self):
        self.assertFalse(rule_matches("Bash(python3 harness/bench_run.py plan *)",
                                      "python3 harness/bench_run.py planx a b"))


class SkillStepCommandsTest(unittest.TestCase):
    def test_commands_are_found(self):
        cmds = step_commands()
        self.assertGreaterEqual(len(cmds), 12, cmds)
        self.assertIn("git fetch origin main", cmds)

    def test_every_batch_child_command_is_one_line_with_no_chaining_or_substitution(self):
        for cmd in step_commands():
            if cmd.startswith(INTERACTIVE_ONLY):
                continue
            with self.subTest(command=cmd):
                bare = re.sub(r"<[^<>]+>", "", cmd)  # `<placeholder>` is not a redirect
                for banned in ("<", ">", "$(", "&&", ";", "|", "`", "\n", "cd "):
                    self.assertNotIn(banned, bare)

    def test_every_batch_child_command_starts_with_an_allowlist_rule_prefix(self):
        bash_rules = [r for r in bra.ALLOWED_TOOLS if r.startswith("Bash(")]
        for cmd in step_commands():
            if cmd.startswith(INTERACTIVE_ONLY):
                continue
            with self.subTest(command=cmd):
                self.assertTrue([r for r in bash_rules if rule_matches(r, cmd)],
                                "no allow rule admits %r" % cmd)

    def test_the_interactive_only_commands_are_the_only_exemptions_and_exist(self):
        exempt = [c for c in step_commands() if c.startswith(INTERACTIVE_ONLY)]
        self.assertTrue([c for c in exempt if c.startswith("python3 harness/bench_run.py grade ")])
        self.assertTrue([c for c in exempt if c.startswith("git restore ")])

    def test_step_3_records_the_starting_branch_and_step_15_returns_to_it_or_the_commit(self):
        cmds = step_commands()
        self.assertIn("git branch --show-current", cmds)
        self.assertIn("git switch --detach <starting-commit>", cmds)
        self.assertIn("git switch <starting-branch>", cmds)
        self.assertNotIn("git switch main", cmds)
        self.assertNotIn("git switch main", skill_steps())

    def test_batch_mode_describes_the_worktree(self):
        text = (REPO / ".claude" / "skills" / "bench-run" / "SKILL.md").read_text(encoding="utf-8")
        batch = text.split("## Batch mode\n", 1)[1].split("\n## One-shot rules\n", 1)[0]
        for fragment in (".claude/worktrees/", "detached at `origin/main`", "never switched or written to",
                         "the batch worktree"):
            self.assertIn(fragment, batch)

    def test_the_argument_hint_offers_a_prompt_id_or_all(self):
        self.assertIn("\nargument-hint: [<prompt-id> | all] [--dry-run]\n", skill_text())

    def test_the_description_says_it_asks_and_adds_no_yaml_special_characters(self):
        line = [ln for ln in skill_text().splitlines() if ln.startswith("description: ")][0]
        self.assertIn("lists the Fable 5.2 arm's prompts", line)
        self.assertIn("asks which to run", line)
        self.assertIn("with all as the argument it runs the whole arm without asking", line)
        self.assertEqual(line.count(": "), 2)  # the key's own and the one that was already there
        self.assertNotIn(" #", line)

    def test_routing_and_batch_mode_name_the_empty_or_all_rule(self):
        text = skill_text()
        phrase = "apart from an optional `--dry-run`, is empty or exactly `all`"
        self.assertEqual(text.count(phrase), 2)
        routing = [ln for ln in text.splitlines() if ln.startswith("You are reading this")][0]
        self.assertIn(phrase, routing)
        self.assertIn(phrase, batch_mode())

    def test_batch_mode_names_the_selection_flags_and_the_invalid_line(self):
        batch = batch_mode()
        for fragment in ("--list", "--select", "--prompts", "INVALID:", "STOP:", "per selected prompt",
                         "Which prompts should run?"):
            self.assertIn(fragment, batch)

    def test_batch_mode_ends_its_turn_after_asking_and_never_interprets_the_answer(self):
        batch = batch_mode()
        self.assertIn("end your turn", batch)
        self.assertIn("verbatim", batch)
        self.assertIn("Never interpret, fix or complete it", batch)
        self.assertIn("--select='<answer>'", batch)

    def test_batch_mode_all_skips_the_question(self):
        flat = " ".join(batch_mode().split())
        self.assertIn("If the arguments contain `all`, go to step 3 with no `--prompts`.", flat)

    def test_batch_mode_asks_again_after_a_bad_answer(self):
        flat = " ".join(batch_mode().split())
        self.assertIn("means nothing was selected: relay it and ask again from (b).", flat)

    def test_every_batch_helper_command_in_the_skill_parses_with_the_helper(self):
        cmds = batch_helper_commands()
        flags = {a for c in cmds for a in c if a.startswith("--")}
        self.assertTrue({"--dry-run", "--list"} <= flags, cmds)
        self.assertTrue([c for c in cmds if any(a.startswith("--select=") for a in c)], cmds)
        for argv in cmds:
            with self.subTest(argv=argv):
                with contextlib.redirect_stderr(io.StringIO()):
                    args = bra.parse_args(argv)
                self.assertEqual(args.model, "claude-fable-5-2")

    def test_the_two_run_commands_take_the_selection_as_an_appended_prompts_flag(self):
        self.assertEqual(batch_mode().count("with `--prompts <selection>` appended when step 2 produced one"), 2)
        runs = [c for c in batch_helper_commands() if "--list" not in c and not any(a.startswith("--select") for a in c)]
        self.assertEqual(len(runs), 2)
        for argv in runs:
            with self.subTest(argv=argv):
                args = bra.parse_args(argv + ["--prompts", "game-melon-jelly,game-lava-lamp"])
                self.assertEqual(bra.resolve_prompts(args.prompts), arm(1, 2))

    def test_the_select_command_takes_the_answer_in_the_equals_form(self):
        (cmd,) = [c for c in batch_helper_commands() if any(a.startswith("--select") for a in c)]
        self.assertEqual([a for a in cmd if a.startswith("--select")], ["--select=1,3-5"])
        self.assertEqual(bra.parse_args(cmd).select, "1,3-5")

    def test_the_steps_run_no_helper_command_so_a_child_never_needs_one(self):
        self.assertNotIn("bench_run_all", skill_steps())
        self.assertIn("No arguments, `all`, or either with `--dry-run` means batch mode", skill_steps())

    def test_steps_open_with_the_one_line_command_instruction(self):
        head = skill_steps().strip().split("\n", 1)[0]
        for phrase in ("one Bash call", "one line", "&&", ";", "pipes", "redirects", "2>&1",
                       "$(...)", "backticks", "heredocs", "cd"):
            self.assertIn(phrase, head)

    def test_steps_never_ask_for_inline_python_or_a_heredoc(self):
        steps = skill_steps()
        self.assertNotIn("<<", steps)
        self.assertNotRegex(steps, r"python3? -c")
        self.assertNotRegex(steps, r"python3? - ")

    def test_the_skill_names_the_bench_run_script_modes_it_runs(self):
        used = {c.split()[2] for c in step_commands() if c.startswith("python3 harness/bench_run.py ")}
        self.assertEqual(used, set(BENCH_RUN_MODES) | {"grade"})

    def test_the_skill_has_no_resolver_code_block_any_more(self):
        text = (REPO / ".claude" / "skills" / "bench-run" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("<<'PY'", text)
        self.assertNotIn("```python", text)
        self.assertIn("harness/bench_run.py", text.split("## Resolver", 1)[1])

    def test_one_shot_rules_and_the_never_line_are_unchanged(self):
        text = (REPO / ".claude" / "skills" / "bench-run" / "SKILL.md").read_text(encoding="utf-8")
        rules = text.split("## One-shot rules\n", 1)[1].split("\n## Steps\n", 1)[0]
        for fragment in (
            "1. The only inputs are the TOML's `[system]` text (if any), its `[user]` text and any listed `[images]`, exactly as printed in step 5. Treat `[system]` as the governing instruction for this answer.",
            "The resolver below is the only thing that touches `results/`, and it prints only paths.",
            "5. After that Write the deliverable is frozen: no Edit, no second Write, no reformatting, no fixes even for an obvious bug, no opening or running it.",
            "**Never:** launch a browser or Playwright, start a dev server or `http.server`, use `open`/`xdg-open`, run the generated code, touch `prompts/`, merge a PR, or enable auto-merge. This skill never writes a playability verdict.",
        ):
            self.assertIn(fragment, rules)


if __name__ == "__main__":
    unittest.main()
