# CLAUDE.md — contributor notes

## Useful commands

- `python -m compileall harness` — syntax-check all harness code (exit 0 expected)
- `python -m unittest discover -s harness/tests -v` — run the harness unit tests
- TOML validation runs in CI (`.github/workflows/ci.yml`) on every PR; `gh pr checks` must be green

## Style

- Conventional commits (`feat:`, `fix:`, `docs:` …), matching the existing git log
- New harness code is stdlib-only Python 3.11+ unless a mode genuinely needs a library (sympy for symbolic math); no other new dependencies without justification in the PR body
