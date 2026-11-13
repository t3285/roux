# `uv sync` on Python 3.14 (some packages build from sdist, which needs a C compiler)

Checked: 2026-11-13

## Cause
- No `.python-version`; `requires-python = ">=3.10, <4"`, so uv picks the default `python3`, here 3.14.
- Several packages in `uv.lock` are versions released before 3.14 and have no cp314 wheels, so uv builds
  them from sdist. That needs a C compiler (`gcc`); without one, the build stops.
- Seen so far: `regex==2024.11.6`, `cffi==1.17.1` (via jupyter -> notebook -> jupyter-server ->
  argon2-cffi -> argon2-cffi-bindings). There may be more after these.
- CI (tox) tests py3.10-3.12, and the classifiers list 3.10-3.12.

## `regex` package: not needed
- No module, test, script or notebook imports `regex` (`import regex` / `from regex`); all uses of the
  word are pandas `filter(regex=...)`, `find -regex`, or the stdlib `re`.
- It was only in `[dependency-groups] dev`, labelled `## docs` (added with `lazydocs` in 675fde6,
  "setting up uv"); `lazydocs` does not depend on it, and nothing else in `uv.lock` does.
- Removed from the dev group on 2026-11-13 (`uv.lock` to be refreshed by `uv sync`/`uv lock`).
- A commented-out `# "regex>=2018.7.11"` remains in `dependencies` (harmless).

## Options
- Use Python 3.12 (the newest in CI): `uv sync --all-extras --python 3.12` (with a 3.12 interpreter
  installed); optionally add a `.python-version` (`3.12`) so plain `uv sync` picks it.
- Or stay on 3.14 and upgrade the locked packages that lack cp314 wheels (`uv lock --upgrade-package cffi ...`);
  3.14 is not yet covered by CI.
- Or install a C compiler, so the sdists build.
