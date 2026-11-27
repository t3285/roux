"""For processing dictionaries."""

from roux.lib.set import itertools, logging, np, pd
from roux.lib.str import dict2str, str2dict  # noqa


def head_dict(d, lines=5):
    return dict(itertools.islice(d.items(), lines))


def sort_dict(d1, by=1, ascending=True):
    """Sort dictionary by values.

    Parameters:
        d1 (dict): input dictionary.
        by (int): index of the value among the values.
        ascending (bool): ascending order.

    Returns:
        d1 (dict): output dictionary.
    """
    return dict(sorted(d1.items(), key=lambda item: item[1], reverse=not ascending))


def merge_dicts(
    l: list,
) -> dict:
    """Merge dictionaries.

    Parameters:
        l (list): list containing the dictionaries.

    Returns:
        d (dict): output dictionary.

    TODOs:
        1. In python>=3.9, `merged = d1 | d2`?
    """
    from collections import ChainMap

    return dict(ChainMap(*l))


def merge_dicts_deep(left: dict, right: dict) -> dict:
    """
    Merge nested dictionaries. Overwrites left with right.

    Parameters:
        left (dict): dictionary #1
        right (dict): dictionary #2

    TODOs:
        1. In python>=3.9, `merged = d1 | d2`?
    """
    # logging.warning("`merge_dicts_deep` is under development.")
    from copy import deepcopy

    d1 = deepcopy(left)
    for k2, v2 in right.items():
        v1 = d1.get(k2)
        if isinstance(v1, dict) and isinstance(v2, dict):
            d1[k2] = merge_dicts_deep(v1, v2)  # recursive
        else:
            d1[k2] = deepcopy(v2)  # overwrite left with right
    return d1


def merge_dict_values(
    l,
    test=False,
):
    """Merge dictionary values.
    Parameters:
        l (list): list containing the dictionaries.
        test (bool): verbose.

    Returns:
        d (dict): output dictionary.
    """
    for di, d_ in enumerate(l):
        if di == 0:
            d = d_
        else:
            d = {k: d[k] + d_[k] for k in d}
        if test:
            print(",".join([str(len(d[k])) for k in d]))
    return d


def flip_dict(d):
    """switch values with keys and vice versa.

    Parameters:
        d (dict): input dictionary.

    Returns:
        d (dict): output dictionary.
    """
    if all([not isinstance(s, list) for s in d.values()]):
        if len(np.unique(list(d.keys()))) != len(np.unique(list(d.values()))):
            logging.warning("values are list.")
            return pd.Series(d).reset_index().groupby(0)["index"].agg(list).to_dict()
        else:
            return {d[k]: k for k in d}
    # else:
    #     if not get_offdiagonal_values(intersections(d)).sum().sum()==0:
    #         raise ValueError('dict values should be mutually exclusive.')
    #     d_={}
    #     for k in d:
    #         for v in d[k]:
    #             d_[v]=k
    #     return d_


def flatten_keys(
    stats,
    sep=":",
    clean=False,
):
    def prep_key(s):
        from roux.lib.str import replace_many
        from roux.lib.sys import to_path

        return to_path(
            replace_many(
                s,
                {
                    ">=": "ge",
                    "<=": "le",
                    "=>": "ge",
                    "=<": "le",
                    "<": "lt",
                    ">": "gt",
                },
                errors=None,
            )
        )

    stats = {
        prep_key(k)
        if not isinstance(k, tuple)
        else sep.join([prep_key(str(s)) for s in k]): v
        for k, v in stats.items()
    }
    if clean:
        ## remove _s
        stats = {
            k.replace(f"_{sep}", sep).replace(f"{sep}_", sep): v
            for k, v in stats.items()
        }
    return stats


def pre_dict(d):
    if isinstance(d, pd.DataFrame):
        df_ = d
        if len(df_) == 1:
            d = df_.iloc[0, :].to_dict()
        else:
            # d=df_.set_index(df_.rd.infer_index()).T.to_dict()
            d = (
                pd.json_normalize(
                    df_.rd.clean().rd.set_index().T.to_dict(),
                    sep=":",
                )
                .iloc[0, :]
                .to_dict()
            )
    elif isinstance(d, pd.Series):
        d = d.to_dict()
    assert isinstance(d, dict), d
    return d


def flatten_vals(d: dict, parent_key: str = "", sep: str = ":") -> dict:
    """
    Flatten a nested dictionary using a specified separator.

    Parameters:
        d (dict): Nested dictionary to flatten.
        parent_key (str): Prefix for the current level.
        sep (str): Separator between nested keys.

    Returns:
        dict: Flattened dictionary.
    """

    d = pre_dict(d)

    items = []
    for k, v in d.items():
        # g: construct the new key with the separator if a parent key exists
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        # g: recursively flatten if the value is a dictionary
        if not isinstance(v, (dict, int, float, str, list, tuple)):
            v = pre_dict(v)

        if isinstance(v, dict):
            items.extend(flatten_vals(v, parent_key=new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def flatten_dict(d, sep=":"):
    d_flat = flatten_vals(d, sep=sep)
    # size=len(d_flat)
    _keys = list(d_flat.keys())

    d_flat = flatten_keys(d_flat, sep=sep)
    # assert len(d_flat)==size,(len(d_flat),size)
    assert len(d_flat) == len(_keys), f"\n{list(d_flat.keys())}\n{_keys}"

    return d_flat


## find
def contains_keys(obj, keys_to_find):
    found = set()

    def recurse(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in keys_to_find:
                    found.add(k)
                recurse(v)
        elif isinstance(o, list):
            for item in o:
                recurse(item)

    recurse(obj)
    return all(k in found for k in keys_to_find)


def diff_dicts(
    d1,  # old
    d2,  # new
    path="",
    ignore=[],
):
    """Recursively find differences between two dictionaries."""
    for k in d1:
        if k not in d2:  # and k not in ignore:
            print(f"{path} ! : '{k}' not in d2")
        else:
            if isinstance(d1[k], dict) and isinstance(d2[k], dict):
                diff_dicts(d1[k], d2[k], f"{path} : {k}" if path else k, ignore=ignore)
            elif d1[k] != d2[k]:
                current_path = f"{path} : {k}" if path else k
                print(f"{current_path}:")
                print(f" - : {d1[k]}")
                print(f" + : {d2[k]}")

    for k in d2:
        if k not in d1:  # and k not in ignore:
            print(f"{path} ! : '{k}' not in d1")


## the stats of plots (`ax.stats`, `roux.viz.io.to_plot`)
def _clean_stats_key(s) -> str:
    """A key of the stats: a label without the counts (`(n)`), the line breaks and the `:` (the separator of the flat keys)."""
    import re

    s = re.sub(r"\(\s*n?=?\s*[\d,]+\s*\)", "", str(s))
    return re.sub(r"\s+", " ", s.replace(":", "-")).strip()


def get_stats_dict(stats) -> dict:
    """
    The stats of a plot (`ax.stats`) as a nested dict.

    Parameters:
        stats (dict|pd.DataFrame|None): e.g. a dict of a correlation (`roux.viz.scatter`), or a table of tests with a row per comparison (`roux.viz.dist.plot_dists`).

    Returns:
        dict: a dict as is (empty if None); a table: `{<row id>: {<column>: <value>}}`, the row id from its text columns that vary between the rows (cleaned: `_clean_stats_key`; nested in their order, e.g. `{<label>: {<subset1>: {<subset2>: {...}}}}`), the values from the other columns (numbers; constant text columns kept; NaN dropped).

    Examples:
        >>> get_stats_dict(pd.DataFrame({'y': ['a\\n(10)', 'b'], 'subset1': 'x', 'subset2': 'z', 'P': [0.1, 0.2]}))
        {'a': {'subset1': 'x', 'subset2': 'z', 'P': 0.1}, 'b': {'subset1': 'x', 'subset2': 'z', 'P': 0.2}}
    """
    import numpy as np
    import pandas as pd

    if stats is None:
        return {}
    if isinstance(stats, dict):
        ## its values made plain too (e.g. a table of tests inside a dict)
        def to_plain(v):
            if isinstance(v, (dict, pd.DataFrame)):
                return get_stats_dict(v)
            if isinstance(v, pd.Series):
                return {str(k): to_plain(x) for k, x in v.items()}
            if isinstance(v, np.ndarray):
                return v.tolist()
            if isinstance(v, np.generic):
                return v.item()
            return v

        return {k: to_plain(v) for k, v in stats.items()}
    if not isinstance(stats, pd.DataFrame):
        raise TypeError(
            f"ax.stats: a dict or a DataFrame, not a {type(stats).__name__}"
        )
    df = stats.reset_index(drop=True).drop(columns=["index"], errors="ignore")
    cols_text = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    ## the row ids: the fewest leading text columns that vary and identify the rows (the later text columns, e.g. a
    ## test's `change`, are values)
    cols_id = []
    for c in [c for c in cols_text if df[c].nunique() > 1]:
        cols_id.append(c)
        if not df.duplicated(subset=cols_id).any():
            break

    def to_value(v):
        if isinstance(v, (np.integer, np.floating, np.bool_)):
            v = v.item()
        return None if isinstance(v, float) and np.isnan(v) else v

    out = {}
    for _, row in df.iterrows():
        values = {
            str(c): to_value(row[c])
            for c in df.columns
            if c not in cols_id and to_value(row[c]) is not None
        }
        if not cols_id:
            ## one comparison (or the same ids): the values directly
            if len(df) > 1:
                raise ValueError(f"rows not identifiable: {df.columns.tolist()}")
            return values
        d = out
        for c in cols_id[:-1]:
            d = d.setdefault(_clean_stats_key(row[c]), {})
        key = _clean_stats_key(row[cols_id[-1]])
        if key in d:
            raise ValueError(f"rows not identifiable by {cols_id}: {key}")
        d[key] = values
    return out


def get_fig_stats(ax) -> dict:
    """
    The stats of a plot: `ax.stats` of its axes (`get_stats_dict`); of the given ax only, if it has some; else those of the figure's axes, `{ax<i>: stats}` (the axes in the figure's order) if several have some.

    Parameters:
        ax (plt.Axes|plt.Figure): the axes returned by the plot, or its figure (then: the figure's axes).

    Returns:
        dict: the stats (empty if none).
    """
    if ax is None:
        return {}
    if getattr(ax, "stats", None) is not None:
        return get_stats_dict(ax.stats)
    fig = getattr(ax, "figure", None) or ax
    axs = {
        f"ax{i}": a.stats
        for i, a in enumerate(getattr(fig, "axes", []))
        if getattr(a, "stats", None) is not None
    }
    if len(axs) == 1:
        return get_stats_dict(list(axs.values())[0])
    return {k: get_stats_dict(v) for k, v in axs.items()}
