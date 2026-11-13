# TODOs

Improvements for this repository, ranked by impact. Assessed on 2026-11-04 at `883025f`.

roux is used as a library: functions and imports that are unused inside the package are part of its
main surface and are kept on purpose. Nothing here proposes removing them. F401 stays ignored.

Evidence: `ruff check roux --isolated --select F,B` (F401 excluded), an import of every module,
runtime reproductions (marked *reproduced*), and the full test suite (16 pass; 6 more need network access, see M2).

---

## High: main functions that raise or return unexpected results

### H1. Undefined names (`NameError` on the affected code path)
Each one is a small fix: a missing import, a misspelled name, or a variable to assign.

| Location | Function | Name | Code path affected |
|---|---|---|---|
| `roux/lib/df.py:465` | `to_sparse` | `dtype` (should be `v`) | whenever `cols` is given (*reproduced*) |
| `roux/viz/image.py:43` | `plot_image` | `kwarg` (param is `kws_to_raster`) | every non-`.png` input (*reproduced*) |
| `roux/viz/annot.py:1059` | `show_stats_by_sides` | `x_center` (not a param) | always: `col_mid` is required, so the branch runs |
| `roux/lib/sys.py:971` | `resolve_paths` | `key` (should be a loop var / `keys`) | when nothing matches: an `UnboundLocalError` replaces the assert message (*reproduced*) |
| `roux/lib/io.py:1364-1368` | `read_tables` | `p` (should be `ps`) | whenever `filterby_time` is given |
| `roux/lib/dfs.py:460` | `merge_by_subset` | `suffixes` | when the subsets do not overlap (the empty-merge fallback) |
| `roux/lib/df.py:1439` | `filter_rows` | `d` (should be `expr`) | `test=True` |
| `roux/viz/ax_.py:1213` | `get_legend2param` | `to_hex` (`from matplotlib.colors import to_hex`) | legend colours given as RGB(A) tuples; **fixed with H5** (local import) |
| `roux/viz/bar.py:405` | `plot_bar_serial` | `num2str` (`from roux.lib.str import num2str`) | always, at the annotation step |
| `roux/workflow/utils.py:4,15,43` | module | `pd`, `makedirs`, `Path` | **the module import itself** (`NameError: pd` at import) |

Related (order-dependent, likely `NameError`): `roux/viz/scatter.py:918`, `plot_volcano_split` reads
`annot_ax1`, which is assigned only in another iteration of the side loop (line 1000). It is reached when that
side is processed first or skipped by `continue` (no rows to annotate).

Already correct (ruff false positives, keep as they are): `dfs.py:369` `merge_dfs` (`k1` is set at the end of
the first iteration) and `set.py:414` `list2ranges` (B020, `zip` is evaluated before the rebinding).

Keeping them fixed: see M1.

Status: open (the `to_hex` row is done)

### H2. Mutable default arguments that are mutated in place (state carried between calls)
The default `[]`/`{}` is shared across calls, so one call changes the behaviour of the next.
Fix: default `None`, then `x = [] if x is None else list(x)` (or `dict(x)`). Keep the
main signatures otherwise.

- `roux/workflow/cfgs.py:326` `read_metadata(config_paths=[])` with `config_paths_auto=True`:
  `config_paths += glob(...)` grows the default, so later calls also read the earlier directories' configs.
- `roux/viz/sets.py:717` `plot_pie(remove_wedges_index=[])`: `+=` accumulates, so later pies drop other wedges.
- `roux/viz/scatter.py:174` `plot_scatter(line_kws={})`: the first call's line colour carries over to later calls.
- `roux/viz/scatter.py:485-489` `_prepare_volcano_data(kws_scatterplot={})`: `hue_order`/`palette` carry over.
- `roux/viz/sets.py:134,186,227` `plot_intersection_counts(sort_cols=..., kws_show_stats={})`.
- `roux/lib/df.py:1222-1224` `query(kws_log={})`: `subset`/`groupby` of one call are logged in later calls.
- `roux/stat/corr.py:212-213` `get_corr(preprocess_kws={}, resample_kws={})`: `verbose=True` carries over.
- `roux/viz/ax_.py:1373` `set_colorbar(bounds=...)`.

The other ~135 mutable defaults (ruff B006) are only read. They can be converted whenever the code is touched.

Status: open

### H3. `str.rstrip(".tar.gz")` strips characters, not a suffix
`roux/lib/io.py:281`, `read_arxv`: `"beta.tar.gz".rstrip(".tar.gz") == "be"` (*reproduced*), so the
in-archive prefix match uses a shorter prefix. `removesuffix(".tar.gz")` does what is intended (py>=3.9; the package needs >=3.10).

Status: open

### H4. Valid scripts from `to_scr` (the wildcard import expansion and the `run()` defaults)
`to_scrs`/`to_pkg` stop at the first notebook whose script does not pass `check_py` (`ruff --select E4,E7,E9,F`).
Reproduced with minimal notebooks through `_to_scr_cleaned(..., force_with_pms=True)` (*reproduced*):
- **Multi-line imports are truncated.** `roux/workflow/function.py:452-466` (`get_global_imports`) filters
  `roux/global_imports.py` line by line, so `from roux.lib.io import (` and `from roux.lib.set import (` lose
  their continuation lines. `replacestar_ruff` (`roux/workflow/io.py:1064`, used by `to_scr(fix=True)` at
  `io.py:446`) pastes them as they are: "Expected one or more symbol names after import". The `select` method
  of `replacestar` (the `df` output) gets the names `(` from them.
  Fix: join every multi-line statement of the block into one line (via `tokenize`; imports without the parentheses).
- **A top-level star import is not expanded.** `to_scr` replaces only `"    from roux.global_imports import *"`
  (`io.py:446`), i.e. inside `run()`. When the import is in a cell before the parameters cell, it stays at the
  module level and ruff reports F403. Fix: in `replacestar_ruff`, with `indent=None`, replace the statement at any
  indentation, each with its own indentation.
- **String defaults are quoted without escaping.** `roux/workflow/pms.py:208-217` (`extract_pms(fmt="str")`,
  used at `io.py:356-371`) evaluates the parameters and wraps a str in `'...'` unless `literal_eval` accepts
  it. So `expr="`col` != 'all'"` -> `expr='`col` != 'all''` and `s="it's"` -> `s='it's'` (not valid syntax).
  `s="1"` -> `s=1` (int instead of str). `p=f"../out/{cfg['version']}.yaml"` -> `p='f"../out/{cfg['version']}.yaml"'`.
  Also `to_scr` strips comments with `s.split("#")[0]` and splits the cell on 4 spaces, which cuts strings
  that contain `#` or 4 spaces.
  Fix: `to_scr` parses the parameters cell with `ast` (`_pms_to_run_args`). A literal default
  (`ast.literal_eval` accepts it) is rendered with `repr()`, as before for numbers, simple strings,
  lists, dicts and `None`. A non-literal default (an f-string, a name, a call, an expression on other parameters)
  is better kept out of the function signature, because it may refer to the notebook's globals or to other
  parameters. It becomes `None`, and the first lines of `run()` restore the notebook's expression:
  `if p is None: p = f"../out/{cfg['version']}.yaml"`, in the order of the cell. Passing `None` explicitly
  therefore gets the notebook's value. Before, an expression on earlier parameters (`y=x*2`) was frozen at
  conversion time (`y=2`). `extract_pms` itself (generated from `examples/roux_workflow_pms.ipynb`) stays as it is.
  Follow-up (CI py3.12, `test_to_scr_pms_defaults`): the restoring lines first used `ast.unparse`, whose output
  depends on the Python version. On 3.12.3 (CI) it gave `f'../out/{cfg['version']}.yaml'` (outer quotes
  reused inside the f-string, PEP 701: valid only on 3.12+). On 3.12.9 it gave the original
  quotes. Fix: copy the cell's source text of the expression (`ast.get_source_segment`) into
  `if p is None: p = <source>`, and indent only its first line, so that multi-line expressions (e.g.
  triple-quoted strings) are kept exactly. The test compares `ast.dump`s, not `ast.unparse` strings, and
  checks the f-string's text in the script. The literal defaults use `repr()`, which is the same on every version.

Plan:
- [x] Phase 1: wildcard import expansion (`get_global_imports` joins multi-line statements; `replacestar_ruff`
  replaces at any indentation) + regression tests in `tests/test_jupytext_input.py`; verify: `driver.py verify`,
  reproduction notebooks A (top-level import) and A2 (import inside `run()`) compile
- [x] Phase 2: `run()` defaults from the parameters cell via `ast` (`_pms_to_run_args`) + regression tests;
  verify: `driver.py verify`, reproduction notebook B compiles and its `run()` defaults are as expected

Notes (not in H4):
- **One star import per notebook.** With two, for example one before the parameters cell (module level) and
  one after it (inside `run()`), the second expansion redefines the names of the first, and `check_py`
  reports F811 (redefinition of unused name), which points right at the duplicate. This behaviour is
  helpful as it is: no change planned.
- **Imported names that the script doesn't use can be removed from the re-wrapped imports.** This is how
  it happens in `to_scr(fix=True)`:
  1. `replacestar_ruff` pastes the joined import lines with their `# noqa`, e.g.
     `from roux.lib.io import read_dict, ..., backup  # noqa`.
  2. Its `post_code` runs `ruff format`, which wraps lines longer than 88 characters back into a
     parenthesised import, one name per line, and moves `# noqa` after the closing `)`.
  3. ruff honours a `# noqa` only on the line where it reports the finding, here the line of each name, so
     the names are no longer covered.
  4. The final `post_code` of `to_scr` runs `ruff check --select E4,E7,E9,F --fix` on the script, and its F401
     fix deletes the unused names.

  Whether F401 is fixable depends on the ruff config that applies to the script: the closest
  `pyproject.toml`/`ruff.toml` above the script, or ruff's defaults if there is none. roux's own config sets
  `unfixable = ["F401"]`, so in this repository the names are kept. `to_scrs`/`to_pkg` write the scripts in
  the notebooks repository (`scr_*/`), where that config doesn't apply, so F401 is fixable there.
  Effect: the names the script uses are kept (the regression test checks `read_dict` and `dropna`). Unused
  names of the wrapped imports (`roux.lib.io`, `roux.lib.set`) are removed, or the whole import if none is
  used, as in reproduction notebook A. The unused single-line imports keep their `# noqa` and stay. The
  script runs the same. Only another module that imports those names from the script (unusual) would
  notice. If that matters, `post_code` could pass `--unfixable F401` to `ruff check`.
- **`extract_pms(fmt="str")` still quotes strings without escaping** (`roux/workflow/pms.py:208-217`).
  Callers: it is main (`__all__` of `roux.workflow.pms`), and `to_scr` still uses it as a fallback
  (`roux/workflow/io.py:414`) when `ast` can't parse the parameters cell. The example notebook uses only
  `fmt="dict"`.
  Benefit of a change: modest.
  - The fallback runs only on a cell that isn't valid Python. `extract_pms` would then also use its regex
    fallback (`_fallback_extract_assignments`), and `check_py` would most likely flag the script anyway.
  - The escaping alone (`repr()` for str values) is a one-line change. It would cover strings with quotes
    or backticks for external callers.
  - Non-literal defaults need more: `_code_string_to_dict` stores the source text (`ast.unparse`)
    of a value it can't evaluate. So the result can't tell the string `'x'` from the expression `x`, and
    `repr()` would turn an f-string into a string literal of its source (valid syntax, different value). The
    full solution is what `_pms_to_run_args` does. It needs the lines that restore the defaults in the function
    body, which a list of `name=value` strings can't carry.
  - `pms.py` is generated from `examples/roux_workflow_pms.ipynb` (nbdev), so any change goes there
    and is then exported.

  Suggestion (Low): make the `repr()` escaping change, and document in the docstring that non-literal
  values come back as their source text. Or deprecate `fmt="str"` in favour of `_pms_to_run_args`.

Status: done

### H5. `sort_legends` on axes without legend entries
`roux/viz/ax_.py:1096`, `sort_legends` (and `drop_duplicate_legend`): with an empty legend,
`zip(*sorted(zip([], [])))` raises `ValueError: not enough values to unpack (expected 2, got 0)` (*reproduced*).
With no legend at all, `get_legend_kws_aes` (`roux/viz/ax_.py:1062`) raises first:
`AttributeError: 'NoneType' object has no attribute 'get_title'`. Seen in a downstream project's CI (roux from
GitHub `master`), in the `format_ax` calls after plots that have no hue.
Fix: `get_legend_kws_aes` returns `{}` without a legend, and `sort_legends` returns the current legend
unchanged when there are no handles.

Plan:
- [x] Phase 1: guard both functions; verify: `driver.py verify` + direct calls on the three cases (no legend,
  empty legend, labels without a legend) and on a normal legend. Also fixes the `to_hex` row of H1
  (`get_legend2param`, same file), which `verify` flagged (F821).

Status: done

---

## Moderate: robustness, test coverage, dependency correctness

### M1. A CI lint step for undefined names
`build.yml` runs tox; `format.yaml` (ruff autofix) is manual. All of H1 is caught by
`ruff check roux --select F821,F811,F823 --isolated` (no F401, so re-exports are unaffected).
Add it as a CI step (with the pinned `ruff==0.15.10`), or add these codes to `[tool.ruff.lint]`.
Also add an "import every module" smoke test: `pkgutil.walk_packages` + `importlib.import_module`
(today only `roux.workflow.utils` needs a fix for it, see H1).

Status: open

### M2. Tests: wider coverage and self-contained runs
- 16 notebooks in `examples/` are ready to become tests, among them ones linked from the README:
  `roux_stat_diff`, `roux_stat_fit`, `roux_stat_norm`, `roux_workflow_cfgs`, `roux_workflow_task`,
  `roux_viz_diagram`, `roux_viz_ds`, plus `roux_lib_log`, `roux_stat_agg`, `roux_viz_blends`,
  `roux_viz_shapes`, `roux_viz_text`, `roux_vizi_select`, `roux_workflow_pms`, `dev_*`.
  Tests for `roux_lib_sys`, `roux_stat_classify`, `roux_viz_ax`, `roux_viz_io`, `roux_viz_theme` are
  commented out in `tests/test_examples.py` (`viz_io`: "debug logging error"; `viz_theme` depends on it).
- Modules without an example or a unit test yet: e.g. `roux.workflow.{task runner paths, nb, function,
  version, monitor}`, `roux.stat.{regress, network, paired, variance, transform}`, `roux.viz.{heatmap, bar,
  compare, image}`. Most of H1/H2 is in these paths, so tests there pay off quickly.
- 6 example tests (`roux_lib_df`, `roux_lib_df_plot`, `roux_lib_io`, `roux_viz_annot`, `roux_viz_dist`,
  `roux_viz_scatter`) download data at run time, so they need network access. Vendor the small
  datasets under `examples/inputs/`, or mark them (`@pytest.mark.network`) so they can be deselected.
- `tests/test_examples.py` appends to the IPython profile (`ipython_config.py`) at import time,
  on every run (the file grows, and it is outside the repository). A temporary `IPYTHONDIR`
  (env var in `tox.ini` / a conftest fixture) keeps the runs self-contained.

Status: open

### M3. Dependency bounds that match the code
- `roux/stat/binary.py:20-21` uses `np.bool`, which is not available in numpy 1.24-1.26 (removed
  in 1.24 and re-added in 2.0), while `numpy>=1.17.3` is allowed. `bool` works on every version.
- `pandas<=2.3.3` keeps pandas 3 out for now. Plan the compatibility work (copy-on-write, string dtype) and then
  raise the bound; until then keep the pin explicit and documented.

Status: open

### M4. Safer evaluation of strings
- `roux/lib/google.py:51` `eval(getpass())` evaluates the pasted client config (a credential) as code:
  `json.loads` reads it as data.
- `roux/lib/str.py:704-716` (string type conversion) uses `eval` on arbitrary strings, including any
  that start with an alphanumeric character: use `ast.literal_eval` (and catch `ValueError, SyntaxError`).
  The current code catches only `ValueError`/`NameError`, so other inputs raise unexpectedly.
- `roux/workflow/version.py:52` `eval(input(...))`: use `ast.literal_eval`.

Status: open

### M5. Robust shell commands (string interpolation with `shell=True`)
10 sites, e.g. `roux/lib/sys.py:572,590,898,935`, `roux/viz/io.py:728,918,933`, `roux/workflow/task.py:781`,
`roux/workflow/io.py:162`, `roux/workflow/workflow.py:251`. Paths with spaces, quotes or `$` are split
or interpreted by the shell. Quote the interpolated paths with `shlex.quote`, or pass argument lists without `shell=True`.

Status: open

### M6. Narrow the bare `except:` clauses (19 sites)
They also catch `KeyboardInterrupt`/`SystemExit` and can mask the actual error. The most useful to narrow are in
`roux/workflow/pms.py:99,105,160,175,215` (parsing of the notebook parameters: an unparsed value is quietly
kept as a string). Narrow them to the expected exceptions, e.g. `(ValueError, SyntaxError)`.

Status: open

### M7. Faster `filter_rows` with a table of rules (was O(rules x rows))
`roux/lib/df.py:1366` (`filter_rows`, `expr` a DataFrame, `fast=False`): one full-length mask per rule
(`expr.iterrows()`). In a downstream workflow, 1,422 rules x ~0.5 M rows took 1.5 min, and a subset with ~13x
the rules and rows was still running after 2.5 h. `fast=True` (numexpr, one `df.eval` of all the rules OR'ed)
is limited in the number of rules: `ValueError: too many inputs`. Fix: per pattern of non-missing columns, a
join of the rows with the (unique) rules of that pattern (O(rows)); same result (missing values in a rule are
wildcards; a rule without values matches all rows); the signature, the pre-filtering of irrelevant rules and
`fast=True` unchanged.

Plan:
- [x] Phase 1: the join for `fast=False`; verify: `driver.py verify` (`test_roux_lib_df`) + the new vs the
  previous implementation (from `git show HEAD`) on random tables (wildcards, str/categorical/int columns,
  duplicated and irrelevant rules, NaN in the data, keep and drop) and a timing on a large table.
  Done 2026-11-13 with a comparison script: 492 cases equal (also categorical rules, a subset of the columns,
  an extra column, a rule without values); 1.8 M rows x 20,000 rules: 0.9 s (200k x 500: 9.4 s -> 0.08 s).
  `verify`: format and imports pass; F821 reports only the 2 names that predate the change (H1: `dtype` line
  465, `d` in `filter_rows`' dict branch); `test_roux_lib_df` needs network access (see M2).

Status: done

### M8. Skip or select `run_tasks` targets with environment variables
Workflows built with roux are often nested: a top-level runner executes "orchestrator" notebooks, each
orchestrator calls `roux.workflow.task.run_tasks('<step>.ipynb', params=..., kernel=...)` for its steps, and
steps may call further steps the same way. Every level runs in its own Jupyter kernel (papermill), so Python
arguments can't reach a `run_tasks` call several levels below; environment variables, though, are inherited by
every kernel and subprocess. They make it possible to skip some steps, or run only some, without editing any notebook.

Feature, in `run_tasks` (`roux/workflow/task.py`), two optional environment variables:
- `ROUX_SKIP_TASKS`: comma-separated fnmatch patterns. A call whose target matches any of them is skipped.
- `ROUX_ONLY_TASKS`: comma-separated fnmatch patterns. When set and non-empty, a call whose target matches none
  of them is skipped.

Rules:
- **Matching:** on the target path as resolved by roux (the existing `Path(script_path).resolve()`). A pattern
  matches the absolute path, the file name or the file stem, so `043_results_data`, `043_results_data.ipynb`
  and `*/nbs_01_x/043_*` all work. Whitespace around patterns is stripped and empty patterns are ignored.
- **Precedence:** a match in `ROUX_SKIP_TASKS` wins over `ROUX_ONLY_TASKS`.
- **When skipped:** one `logging.warning` naming the target and the variable; return early (no setup, no cache
  dir, no report notebook, no runner call), with the same kind of value `run_tasks` returns when there is
  nothing to run (e.g. every task dropped because its outputs exist), so callers handle it as usual.
- **Neither variable set, or both empty:** behaviour exactly as before.
- **Where:** the same point for every runner (`py`, `bash`, `slurm`, auto): after the target path is resolved,
  before any work. main signature unchanged, no new required arguments.
- **Docs:** both variables in the `run_tasks` docstring (`Notes:`), with a short example:
  ```
  ROUX_SKIP_TASKS="043_results_data,*/notebooks_scripts/*" python runner.py
  ```
  Also in `.claude/CLAUDE.md` or a docs page, if one lists environment variables.

Tests (a small test that runs no notebook: a tiny notebook/script in a tmp dir, or a stubbed runner;
`monkeypatch.setenv` / `delenv`): unset -> the call goes ahead; skip by stem, by name and by path glob;
only-list -> non-matching targets are skipped; skip-and-only overlap -> skipped; empty strings -> no effect.

Process: the `roux-change` skill (phases, `driver.py verify` after each, review before commit). Report per
phase: `git diff --stat` and the relevant hunks, the `verify` result, a proposed commit message, and one
example log line of a skipped call.

Status: open

### M9. `run_tasks`: the kernel for the bash/slurm runners, a configurable cache dir, running tagged cells
From the datasets repository (its T17), found while running `notebooks/run.ipynb` stages on a machine without the
notebooks' kernel:
- `roux/workflow/task.py:864-878` (`to_sbatch_script`): the papermill command for `.ipynb` has the kernel commented
  out (`# kernel_name=kernel,`, `# --kernel`), and `run_tasks` (`:1468-1479`, `kws_runner`) does not pass `kernel`.
  So with the `bash` (and `slurm`) runner, `run_tasks(nb, kernel='python3')` runs the notebook with the kernel in
  its own metadata (`NoSuchKernel: No such kernel named datasets`). The `py` runner does pass it (`:1414`).
- `roux/workflow/task.py:1199`: `cache_dir_path="~/scratch/.roux"` is fixed. Run from nested notebooks (where the
  argument can't be reached), it writes outside the work directory, e.g. in a sandbox limited to it. An
  environment variable (`ROUX_CACHE_DIR`), inherited by every kernel, makes it configurable without editing notebooks.
- A helper to run the tagged code cells of a notebook as a plain script (no kernel), e.g. one stage of a runner
  notebook, with a dry mode that only prints the `run_tasks` params. Modelled on `datasets/notebooks/run_cells.py`.

Plan:
- [x] Phase 1: `kernel` passed to papermill by `to_sbatch_script` (when given) and from `run_tasks`;
  `cache_dir_path=None` -> `$ROUX_CACHE_DIR` or `~/scratch/.roux`; docstrings; verify: `driver.py verify` + direct
  calls: the command in a `run.sh` written by `to_sbatch_script` with/without a kernel, and the resolved cache dir
  with/without the variable.
- [x] Phase 2: `run_cells` in `roux/workflow/task.py` (+ `roux run-cells` CLI); verify: `driver.py verify` + a run
  on a small tagged notebook in a tmp dir (tags, params, dry mode).

Status: done

---

## Low: correctness details, hygiene, metadata

- L1. `roux/lib/log.py:41-42`: duplicate dict key `"🛑"` (`critical`, then `fatal`), so the custom
  `critical` level/format is replaced and `Logger.critical` uses the plain style. A distinct key restores it.
- L2. `roux/lib/df.py:863` `assert False, valids` in `assert_dense`, and ~200 `assert`s used for input
  validation, are skipped under `python -O`. Use `raise AssertionError(...)` / `ValueError` in main
  functions, at least where the assert is the only check.
- L3. Unused locals that hint at options worth wiring up (F841): `viz/annot.py:1001-1006`
  `show_dists_stats` (`text_va`, `text_ha`, `text_pad`, `mid_pos`), `viz/compare.py:62` (`colx`, `coly`),
  `viz/dist.py:340` (`x_stat`), `viz/annot.py:151` (`text_func`), `workflow/workflow.py:169` (`packagen`).
  Check whether each was meant to be passed on.
- L4. Closures over loop variables (B023, 16): mostly lambdas applied immediately (safe); review
  `workflow/monitor.py:42-44` and `viz/sets.py:130`.
- L5. `raise ... from err` in `except` blocks (B904, 7) to keep the original traceback.
- L6. `to_scr` writes scratch files into `./.to_src/` of the current directory (`workflow/io.py:312,325`),
  which shows up as an untracked dir in the repository it runs from (`to_pkg`, `to_scrs`). A temp dir keeps it clean.
- L7. Version metadata to align: `pyproject.toml` 0.1.4 vs `CITATION.cff` and the README citation 0.1.2.
  A `roux.__version__` would be handy (`importlib.metadata.version("roux")`).

Status: open (L1-L7)
