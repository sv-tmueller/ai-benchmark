"""Unit tests for ``bench_run_all.py``, the batch driver behind ``/bench-run``.

No test here may reach the real ``claude`` binary. Children are started
through a fake ``claude`` executable written into a temp dir; ``git`` and
``gh`` go through the helper's single ``_run`` seam, which the tests patch.
"""

import contextlib
import io
import json
import os
import re
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
with open(os.path.join(d, "calls.jsonl"), "a") as f:
    f.write(json.dumps({
        "argv": argv, "cwd": os.getcwd(), "env_names": sorted(os.environ),
        "effort": os.environ.get("CLAUDE_EFFORT"),
        "stdin_is_devnull": os.path.samestat(os.fstat(0), os.stat(os.devnull)),
        "sid": os.getpgrp() == os.getpid(),
    }) + "\n")
if beh.get("sleep"):
    time.sleep(beh["sleep"])
if "stdout_raw" in beh:
    sys.stdout.write(beh["stdout_raw"])
else:
    sys.stdout.write(json.dumps(beh.get("json", {"type": "result", "result": "ok"})))
sys.exit(beh.get("exit", 0))
'''


def result_json(text="ok", **kw):
    d = {"type": "result", "subtype": "success", "is_error": False, "result": text,
         "permission_denials": [], "modelUsage": {"claude-fable-5-2": {}}}
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
            "PATH": os.environ["PATH"], "HOME": str(self.dir),
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

    def test_unparseable_output_gives_no_json_and_no_text(self):
        out = self.summarize(None, stdout="not json SECRET")
        self.assertFalse(out.parsed)
        self.assertIsNone(out.stop_line)
        self.assertNotIn("SECRET", repr(out))


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

    def test_nonzero_exit_is_reported(self):
        self.scenario({"help": EFFORT_HELP, "default": {"exit": 3}})
        self.assertEqual(self.launch().exit_code, 3)

    def test_timeout_kills_the_child_and_returns_quickly(self):
        self.scenario({"help": EFFORT_HELP, "default": {"sleep": 60}})
        start = time.monotonic()
        run = self.launch(timeout=1)
        self.assertTrue(run.timed_out)
        self.assertLess(time.monotonic() - start, 20)

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


if __name__ == "__main__":
    unittest.main()
