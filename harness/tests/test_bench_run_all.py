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
eff = beh.get("effects", {})
if eff:
    sp = os.path.join(d, "state.json")
    st = json.load(open(sp))
    if eff.get("open_pr"):
        n = st["next_pr"]
        st["next_pr"] = n + 1
        st["prs"].append({"number": n, "url": "https://example.test/pull/%d" % n,
                          "files": [{"path": sc["files"][pid]}]})
    for rel in eff.get("write", []):
        path = sc["files"][pid] if rel == "{target}" else rel
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write("SECRET-DELIVERABLE")
    if "branch" in eff:
        st["branch"] = eff["branch"]
    if "dirty_tracked" in eff:
        st["dirty_tracked"] = eff["dirty_tracked"]
    json.dump(st, open(sp, "w"))
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

    The working-tree state is the real temp repo directory (untracked = any
    file outside ``prompts/`` and ``harness/``); branch, PRs and so on live in
    ``state.json``, which the fake claude can change too.
    """

    def __init__(self, case):
        self.case = case
        self.calls = []

    def state(self):
        return json.loads((self.case.dir / "state.json").read_text())

    def save(self, st):
        (self.case.dir / "state.json").write_text(json.dumps(st))

    @staticmethod
    def done(out="", rc=0, err=""):
        return subprocess.CompletedProcess([], rc, out, err)

    def untracked(self):
        repo = self.case.repo
        found = []
        for p in sorted(repo.rglob("*")):
            rel = p.relative_to(repo).as_posix()
            if p.is_file() and not rel.startswith(("prompts/", "harness/")):
                found.append(rel)
        return found

    def __call__(self, cmd, cwd=None, timeout=None):
        self.calls.append(list(cmd))
        st = self.state()
        if cmd[0] not in ("git", "gh"):
            return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        if cmd[:3] == ["git", "fetch", "origin"]:
            return self.done()
        if cmd == ["git", "branch", "--show-current"]:
            return self.done(st["branch"] + "\n")
        if cmd == ["git", "rev-parse", "HEAD"]:
            return self.done(st["head"] + "\n")
        if cmd == ["git", "rev-parse", "origin/main"]:
            return self.done(st["origin_main"] + "\n")
        if cmd[:2] == ["git", "status"]:
            lines = [" M " + p for p in st["dirty_tracked"]] + ["?? " + p for p in self.untracked()]
            return self.done("".join(line + "\n" for line in lines))
        if cmd[:4] == ["git", "ls-tree", "-r", "--name-only"]:
            return self.done("".join(p + "\n" for p in st["main_files"]))
        if cmd == ["git", "switch", "main"]:
            st["branch"] = "main"
            self.save(st)
            return self.done()
        if cmd == ["gh", "auth", "status"]:
            return self.done(rc=0 if st["gh_ok"] else 1, err="" if st["gh_ok"] else "not logged in")
        if cmd[:3] == ["gh", "pr", "list"]:
            return self.done(json.dumps(st["prs"]))
        raise AssertionError("unexpected command %r" % (cmd,))


def readme_ledger():
    """(prompt id, target path) rows of the README Fable 5.2 ledger table."""
    text = (REPO / "README.md").read_text(encoding="utf-8")
    return re.findall(r"^\| `([a-z0-9-]+)` \|[^\n]*\| `(results/[^`]+)` \|", text, re.M)


class BatchCase(FakeClaudeCase):
    def setUp(self):
        super().setUp()
        (self.repo / "prompts").mkdir()
        for p in (REPO / "prompts").glob("*.toml"):
            if not p.name.endswith(".fixtures.toml"):
                (self.repo / "prompts" / p.name).write_text(p.read_text(encoding="utf-8"))
        self.targets = dict(readme_ledger())
        self.git = FakeGit(self)
        self.git.save({"branch": "main", "head": "abc", "origin_main": "abc", "gh_ok": True,
                       "main_files": [], "prs": [], "dirty_tracked": [], "next_pr": 1})
        self.set_children()

    def set_children(self, by_prompt=None, default=None, help_text=EFFORT_HELP):
        base = {"json": result_json("done"), "effects": {"open_pr": True}}
        base.update(default or {})
        self.scenario({"help": help_text, "files": self.targets,
                       "default": base, "by_prompt": by_prompt or {}})

    def batch(self, *extra, model="claude-fable-5-2", timeout="60", env=None):
        argv = ["--model", model, "--claude", str(self.bin), "--timeout", timeout,
                "--log-dir", str(self.dir / "logs"), *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(bra, "_run", self.git):
            code = bra.main(argv, environ=env or self.env, repo_root=self.repo)
        return code, out.getvalue()

    def report_lines(self, out):
        return {m.group(1): (m.group(2), m.group(3)) for m in
                re.finditer(r"(?m)^((?:game|app)-[a-z-]+)  (.+?)  (\S+)$", out)}

    def called_ids(self):
        return [c["argv"][c["argv"].index("-p") + 1].split()[1] for c in self.calls()]


class ArmDataTest(unittest.TestCase):
    def test_arm_prompts_match_the_readme_ledger_in_order(self):
        self.assertEqual(list(bra.ARM_PROMPTS), [pid for pid, _ in readme_ledger()])
        self.assertEqual(len(bra.ARM_PROMPTS), 11)

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
                name = bra.expected_name(REPO, pid, "claude-fable-5-2")
                self.assertEqual(Path(target).name, name)


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
        st = self.git.state()
        st["branch"] = "feat/x"
        self.git.save(st)
        self.assert_no_child(*self.batch())

    def test_head_behind_origin_main_stops_before_any_child(self):
        st = self.git.state()
        st["origin_main"] = "def"
        self.git.save(st)
        self.assert_no_child(*self.batch())

    def test_untracked_file_stops_before_any_child(self):
        (self.repo / "scratch.txt").write_text("x")
        self.assert_no_child(*self.batch())

    def test_modified_tracked_file_stops_before_any_child(self):
        st = self.git.state()
        st["dirty_tracked"] = ["README.md"]
        self.git.save(st)
        self.assert_no_child(*self.batch())

    def test_gh_auth_failure_stops_before_any_child(self):
        st = self.git.state()
        st["gh_ok"] = False
        self.git.save(st)
        self.assert_no_child(*self.batch())


class BatchLoopTest(BatchCase):
    def test_a_clean_run_attempts_all_eleven_in_order_and_reports_each_pr(self):
        code, out = self.batch()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.called_ids(), list(bra.ARM_PROMPTS))
        rep = self.report_lines(out)
        self.assertEqual(list(rep), list(bra.ARM_PROMPTS))
        self.assertEqual(rep["game-melon-jelly"], ("pr-opened #1", "https://example.test/pull/1"))
        self.assertEqual(rep["game-weichensteller"], ("pr-opened #11", "https://example.test/pull/11"))

    def test_every_child_gets_the_model_and_the_effort_level(self):
        self.batch()
        for call in self.calls():
            argv = call["argv"]
            self.assertEqual(argv[argv.index("--model") + 1], "claude-fable-5-2")
            self.assertEqual(argv[argv.index("--effort") + 1], "high")

    def test_progress_lines_come_before_the_report(self):
        _, out = self.batch()
        first_progress = out.index("[1/11] game-melon-jelly")
        self.assertLess(first_progress, out.index("game-melon-jelly  pr-opened"))

    def test_prompt_on_origin_main_is_skipped(self):
        st = self.git.state()
        st["main_files"] = ["results/melon-jelly/melon-jelly_claude_fable_5_2.html"]
        self.git.save(st)
        code, out = self.batch()
        self.assertNotIn("game-melon-jelly", self.called_ids())
        self.assertEqual(len(self.calls()), 10)
        self.assertEqual(self.report_lines(out)["game-melon-jelly"][0], "skipped: on origin/main")

    def test_prompt_in_an_open_pr_is_skipped_with_its_url(self):
        st = self.git.state()
        st["prs"] = [{"number": 42, "url": "https://example.test/pull/42", "files": [
            {"path": "results/lava-lamp/lava-lamp_claude_fable_5_2.html"}]}]
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
            "game-meridian-launch": {"json": result_json("x\nrun void, re-run in a fresh session"),
                                     "effects": {}},
            "game-sunset-ocean": {"json": result_json("x", is_error=True, subtype="error_during_execution"),
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
        self.assertIn("run void", rep["game-meridian-launch"][0])
        self.assertEqual(rep["game-sunset-ocean"][0], "failed: error_during_execution")
        self.assertTrue(rep["game-horror-house"][0].startswith("pr-opened"))
        self.assertEqual(len(rep), 11)
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
        self.assertRegex(out, r"(?m)^pr-opened: 11$")
        self.assertIn("log folder: %s" % (self.dir / "logs"), out)
        self.assertTrue((self.dir / "logs" / "game-melon-jelly.json").exists())

    def test_default_log_folder_is_outside_the_repo(self):
        with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": str(self.dir / "cache")}):
            folder = bra.make_log_dir(None)
        self.assertTrue(str(folder).startswith(str(self.dir / "cache" / "bench-run")))
        self.assertNotIn(self.repo, folder.parents)

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
        self.assertEqual(len(self.calls()), 11)
        self.assertFalse((self.repo / self.targets["game-melon-jelly"]).exists())
        name = Path(self.targets["game-melon-jelly"]).name
        moved = self.dir / "logs" / "leftovers" / "game-melon-jelly" / name
        self.assertTrue(moved.is_file())
        self.assertEqual(moved.read_text(), "SECRET-DELIVERABLE")
        self.assertNotIn("SECRET", out)

    def test_a_clean_tree_on_another_branch_is_switched_back_to_main(self):
        self.set_children(by_prompt={"game-melon-jelly": {"effects": {"branch": "feat/9-x"}}})
        self.batch()
        self.assertIn(["git", "switch", "main"], self.git.calls)
        self.assertEqual(len(self.calls()), 11)

    def test_a_foreign_untracked_file_halts_the_batch_and_skips_the_merge_step(self):
        self.set_children(by_prompt={"game-lava-lamp": {
            "effects": {"write": ["results/lava-lamp/stray.txt"]}}})
        code, out = self.batch()
        self.assertEqual(self.called_ids(), ["game-melon-jelly", "game-lava-lamp"])
        rep = self.report_lines(out)
        self.assertEqual(rep["game-minecraft"][0], "not-started: tree dirty after game-lava-lamp")
        self.assertEqual(rep["game-weichensteller"][0], "not-started: tree dirty after game-lava-lamp")
        self.assertTrue((self.repo / "results/lava-lamp/stray.txt").exists())  # never touched
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
        self.assertNotIn(["git", "switch", "main"], self.git.calls)
        self.assertEqual(self.called_ids(), ["game-melon-jelly"])


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

    def test_merge_script_runs_after_cleanup_returned_to_main(self):
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
                                    ["gh", "pr"]), cmd)
        self.assertNotIn(["git", "switch", "main"], self.git.calls)

    def test_dry_run_shows_run_and_skip_per_prompt(self):
        st = self.git.state()
        st["main_files"] = ["results/melon-jelly/melon-jelly_claude_fable_5_2.html"]
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
        (self.repo / "scratch.txt").write_text("x")
        code, out = self.batch("--dry-run")
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"(?m)^check FAIL: clean tree")
        self.assertEqual(self.calls(), [])

    def test_dry_run_prints_the_stop_line_for_a_missing_effort(self):
        env = {k: v for k, v in self.env.items() if k != "CLAUDE_EFFORT"}
        code, out = self.batch("--dry-run", env=env)
        self.assertNotEqual(code, 0)
        self.assertRegex(out, r"(?m)^STOP: .*CLAUDE_EFFORT")


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
            "**Never:** launch a browser or Playwright, start a dev server or `http.server`, use `open`/`xdg-open`, run the generated code, touch `prompts/`, merge a PR, or enable auto-merge. The only code that runs a result is `harness/grade.py`'s own execution modes. This skill never writes a playability verdict.",
        ):
            self.assertIn(fragment, rules)


if __name__ == "__main__":
    unittest.main()
