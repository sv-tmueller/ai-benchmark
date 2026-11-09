---
name: bench-run
description: One-shot a single benchmark prompt in this session and file the result: deliverable plus meta sidecar under results/, a grading sidecar where the prompt has a [grading] rule, one issue, one branch, one PR that closes it. No orchestrator, no agents, never merges, never launches a browser. User-invocable only.
disable-model-invocation: true
argument-hint: <prompt-id> [--dry-run]
---

You are reading this because the user typed `/bench-run <prompt-id>`. The arguments are in `$ARGUMENTS`: a prompt id (or a TOML file stem) and an optional `--dry-run`. Do exactly what follows, in order. This is a plain in-session one-shot: no orchestrator, no agent team, no repair round.

The model under test is **you**. The model id is the exact one stated in your system prompt (for example `claude-fable-5-2`). If you do not know it with certainty, stop and ask the user; never guess.

## One-shot rules

1. The only inputs are the TOML's `[system]` text (if any), its `[user]` text and any listed `[images]`, exactly as printed in step 5. Treat `[system]` as the governing instruction for this answer.
2. Until the deliverable is written, do not read, cat, grep, list or search anything under `results/`, `README.md`, `decks/`, the gallery, or issues and PRs about earlier runs of this prompt. The resolver below is the only thing that touches `results/`, and it prints only paths.
3. Generate the whole deliverable in one pass and write it with exactly one Write call to the target path. No drafts, no scratch files, no split writes. No tool calls between reading the prompt and that Write: no search, no fetching docs or libraries, no running code.
4. The content is the answer exactly as the prompt asks for it:
   - html: the file starts with `<!DOCTYPE html>`, with no markdown fences and no commentary.
   - md blueprint: one markdown document with every project file as a fenced code block labelled with its path.
   - text: only the answer the prompt asks for.
5. After that Write the deliverable is frozen: no Edit, no second Write, no reformatting, no fixes even for an obvious bug, no opening or running it.

If any of these rules was broken, or the Write failed, the run is **void**: delete the files you wrote, create no issue, and report "run void, re-run in a fresh session".

**Never:** launch a browser or Playwright, start a dev server or `http.server`, use `open`/`xdg-open`, run the generated code, touch `prompts/`, merge a PR, or enable auto-merge. The only code that runs a result is `harness/grade.py`'s own execution modes. This skill never writes a playability verdict.

## Steps

1. **Parse arguments.** First token is `<prompt-id>`; `--dry-run` may follow.
2. **Fresh-session guard.** If this session has already read, discussed or generated any result for this prompt, or any other benchmark generation, stop and ask for a fresh session. One prompt per session.
3. **Preflight** (skipped by `--dry-run` except `git fetch origin main`):
   - `git fetch origin main`, and `HEAD` must equal `origin/main`; otherwise tell the user to switch and pull.
   - `git status --porcelain --untracked-files=no` must be empty, and there must be no untracked files under `results/` or `prompts/`.
   - `gh auth status` must succeed.
4. **Plan.** Run the resolver (below) in `plan` mode from the repo root. It stops with a `STOP:` line if the prompt, folder, extension or model tag cannot be resolved, or if any target already exists locally, on `origin/main` or in an open PR. Relay a stop to the user and end. With `--dry-run`, show the plan output and end here: no writes, no issue, no branch, no PR (the resolver makes only read-only `git` and `gh` calls).
5. **Print the prompt verbatim:** `python -c "import tomllib,sys; d=tomllib.load(open(sys.argv[1],'rb')); print(d.get('system',{}).get('text','')); print('-----'); print(d['user']['text'])" prompts/<toml>` using the `toml` value from the plan. If the TOML has `[images]`, Read those files (read-only).
6. **Generate** the deliverable and Write it to the planned target path (one Write, see the one-shot rules).
7. **Meta.** Run the resolver in `meta` mode. It requires the deliverable to exist and be non-empty and writes the sidecar shown in the plan preview, with `generated_utc` stamped now.
8. **Grade only if the plan says a grading mode** (the TOML has `[grading]`): run `python harness/grade.py --prompt <id>` and keep its output for the PR body. On a non-zero exit, keep the result, commit no grading sidecar and report the error line (for example a missing sympy). Without `[grading]`, skip this step and write nothing about playability.
9. **Scope check.** `git status --porcelain --untracked-files=all` must show only the run's own 2 or 3 new paths (deliverable, meta, and the grading sidecar if one was produced). `grade.py --prompt` can rewrite the sidecars of other models' results for the same prompt; restore any such file with `git restore -- <path>` and mention it in the PR.
10. **Issue.** `gh issue create` with the title and body below; note the number `N`.
11. **Branch.** `git switch -c <branch>`; the untracked new files carry over.
12. **Commit.** `git add` each run path explicitly. `git diff --cached --name-only` must equal exactly the run's own paths, with nothing under `prompts/`. Commit with the message below. Follow the session's own commit attribution rules; this skill does not prescribe any.
13. **Push.** `git push -u origin <branch>`.
14. **PR.** `gh pr create` with the title and body below, containing `Closes #N`. Never run `gh pr merge` and never enable auto-merge.
15. **Return.** Switch back to the branch you started on (normally `main`). Report the issue and PR URLs, the paths, the grading result and the next step: for game and app results, browser verification on a stronger machine, whose verdict is added later in its own commit outside this skill.

## Naming

`<tag->` is the model tag with `_` replaced by `-`; `<prefix>`, `<tag>` and the paths come from the plan output.

- **Issue title:** `<prompt-id>: <model-id> one-shot result`. Body: what runs (`prompts/<toml>`, plain one-shot through /bench-run, no orchestrator or agents), the target paths and the deliverable kind.
- **Branch:** `feat/<N>-<prefix>-<tag->-result`.
- **Commit:** `feat(results): add <prefix> <model-id> one-shot result (#N)`.
- **PR title:** `<prefix> (<model-id>, one-shot): result`. Body sections: summary (with the one-shot statement), files, grading (the grade.py output, or "no [grading] rule; no playability verdict written; browser verification pending"), in-session caveats (temperature, max_tokens, usage not observable), and `Closes #N`.

## Resolver

Run from the repo root (not with `-I`, so the `harness` import works). Replace `<prompt-id>` and `<model-id>`; the mode is `plan` or `meta`. It needs `python` 3.11+ and read-only `git` and `gh`. In `plan` mode it prints only `key: value` lines and a meta preview, never any content from a result file.

```bash
python - "<prompt-id>" "<model-id>" plan <<'PY'
import json, re, subprocess, sys, tomllib
from datetime import datetime, timezone
from pathlib import Path

arg, model, mode = sys.argv[1:4]
sys.path.insert(0, ".")
from harness.modes._common import derive_model


def stop(msg):
    print("STOP: " + msg)
    sys.exit(1)


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


# 1. prompt: id match, else TOML stem; exactly one; no parametrized prompts
tomls = [p for p in sorted(Path("prompts").glob("*.toml")) if not p.name.endswith(".fixtures.toml")]
data = {p: tomllib.loads(p.read_text(encoding="utf-8")) for p in tomls}
hits = [p for p in tomls if data[p].get("id") == arg] or [p for p in tomls if p.stem == arg]
if len(hits) != 1:
    stop("%d prompts match %r; need exactly one" % (len(hits), arg))
tpath = hits[0]
prompt = data[tpath]
pid = prompt["id"]
if Path("prompts", tpath.stem + ".fixtures.toml").exists():
    stop("%s is parametrized (has a fixtures file); refusing" % pid)

# 2. folder from existing metas of this prompt
metas = []
for m in sorted(Path("results").glob("*/*.meta.json")):
    try:
        meta = json.loads(m.read_text(encoding="utf-8"))
    except ValueError:
        continue
    if meta.get("prompt_id") == pid:
        metas.append((m, meta))
folders = sorted({m.parent.name for m, _ in metas})
if len(folders) != 1:
    stop("%d results folders for %s %s; ask the user which one" % (len(folders), pid, folders))
folder = folders[0]

# 3. prefix, 4. extension
prefix = prompt.get("file_prefix") or tpath.stem
exts = {Path(meta["outputs"]["deliverable"]).suffix.lstrip(".") for _, meta in metas
        if isinstance(meta.get("outputs"), dict) and meta["outputs"].get("deliverable")}
ext = prompt.get("save_as") or (exts.pop() if len(exts) == 1 else None)
if not ext:
    stop("cannot determine the extension (save_as unset, metas give %s)" % sorted(exts))

# 5. deliverable kind
if ext == "html":
    kind = "single HTML file"
elif ext == "md" and prompt.get("category") in ("game-generation", "app-generation"):
    kind = "single markdown blueprint"
else:
    kind = "text answer"

# 6. model tag from the session model id, 7. harness agreement
model_id = re.sub(r"\[[^\]]*\]$", "", model.strip())
tag = re.sub(r"[^a-z0-9]+", "_", re.sub(r"-\d{8}$", "", model_id).lower())
if not re.fullmatch(r"[a-z][a-z0-9_]*[a-z0-9]", tag):
    stop("model tag %r from %r is not usable" % (tag, model))
base = "results/%s/%s_%s" % (folder, prefix, tag)
target, meta_path, grade_path = "%s.%s" % (base, ext), base + ".meta.json", base + "_grading.json"
if derive_model(Path(target), prompt) != tag:
    stop("harness derive_model disagrees with tag %s for %s" % (tag, target))

# 8. no overwrite: disk, origin/main, open PRs
for p in ((target,) if mode == "plan" else ()) + (meta_path, grade_path):
    if Path(p).exists():
        stop("%s already exists on disk" % p)
for p in (target, meta_path, grade_path):
    if sh("git", "cat-file", "-e", "origin/main:" + p).returncode == 0:
        stop("%s already exists at origin/main" % p)
prs = sh("gh", "pr", "list", "--state", "open", "--limit", "200", "--json", "number,files")
if prs.returncode:
    stop("gh pr list failed: " + prs.stderr.strip())
for pr in json.loads(prs.stdout):
    if any(f["path"] == target for f in pr["files"]):
        stop("open PR #%d already touches %s" % (pr["number"], target))
if mode == "meta" and (not Path(target).is_file() or Path(target).stat().st_size == 0):
    stop("%s is missing or empty; write the deliverable first" % target)

# meta sidecar (Fable 5.1 shape plus the one-shot keys)
def given(key, name):
    return "%s %s" % (name, prompt[key]) if key in prompt else "%s not set in the TOML" % name

sidecar = {
    "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if mode == "meta"
    else "<UTC timestamp stamped in meta mode>",
    "toml": tpath.name,
    "prompt_id": pid,
    "title": prompt.get("title"),
    "endpoint": "none (generated in-session by Claude Code via /bench-run, plain one-shot; no orchestrator, no agents, no repair round)",
    "model": model_id,
    "one_shot": True,
    "edits_after_generation": 0,
    "params": {
        "temperature": None,
        "max_tokens_requested_initial": None,
        "reasoning_effort": None,
        "note": "Sampling settings from the TOML (%s) could not be applied in-session; session defaults applied. "
        "The Claude Code system context was present alongside the TOML system text. "
        "finish_reason and usage are not observable in-session." % (
            given("temperature", "temperature") + "; " + given("max_tokens", "max_tokens")),
    },
    "finish_reason": None,
    "truncated": False,
    "usage": None,
    "retries": [],
    "num_retry_api_calls": 0,
    "grading": None,
    "outputs": {"deliverable": target},
}
text = json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n"

# 9. output
gmode = (prompt.get("grading") or {}).get("mode")
dash = tag.replace("_", "-")
print("prompt_id: " + pid)
print("toml: " + tpath.name)
print("folder: results/" + folder)
print("prefix: " + prefix)
print("extension: " + ext)
print("kind: " + kind)
print("model_tag: " + tag + " (harness derive_model agrees)")
print("target: " + target)
print("meta: " + meta_path)
print("grading_sidecar: " + grade_path)
print("grading_mode: " + (gmode or "none"))
print("grade_command: " + ("python harness/grade.py --prompt " + pid if gmode else "none (no [grading] rule)"))
print("issue_title: %s: %s one-shot result" % (pid, model_id))
print("branch: feat/<N>-%s-%s-result" % (prefix, dash))
print("commit: feat(results): add %s %s one-shot result (#<N>)" % (prefix, model_id))
print("pr_title: %s (%s, one-shot): result" % (prefix, model_id))
if mode == "meta":
    Path(meta_path).write_text(text, encoding="utf-8")
    print("written: " + meta_path)
else:
    print("meta_preview:")
    print(text, end="")
PY
```

The sidecar never contains `playability_verification` or `playability` keys; `grade.py` then skips a game result instead of failing it. A later browser check, outside this skill, adds them in its own commit.
