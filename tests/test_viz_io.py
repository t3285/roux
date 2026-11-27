"""`roux.viz.io.to_plot`: the stats saved with a plot."""

import matplotlib

matplotlib.use("Agg")


def _plot(tmp_path, stats, ax_stats=None, pass_ax=False):
    import matplotlib.pyplot as plt
    import pandas as pd

    from roux.lib.io import read_dict
    from roux.viz.io import to_plot

    plt.close("all")
    fig, ax = plt.subplots()
    ax.plot([1, 2], [1, 2])
    if ax_stats is not None:
        ax.stats = ax_stats
    plotp = str(tmp_path / "plots/a.png")
    to_plot(
        ax if pass_ax else plotp,
        **({"prefix": str(tmp_path / "plots") + "/"} if pass_ax else {}),
        data=pd.DataFrame({"x": [1, 2]}),
        stats=stats,
        fmts=["png"],
        logp=str(tmp_path / "missing.log"),
    )
    plt.close("all")
    p = next((tmp_path / "plots").rglob("stats.yaml"), None)
    return None if p is None else read_dict(str(p))


def test_to_plot_stats_merged(tmp_path):
    """The given stats + the plot's ax.stats (the given ones win), flat keys."""
    assert _plot(
        tmp_path, {"n": 2, "a": {"P": 0.1}}, ax_stats={"a": {"P": 0.5, "r": 0.3}}
    ) == {"a:P": 0.1, "a:r": 0.3, "n": 2}


def test_to_plot_stats_ax_given(tmp_path):
    """The axes given as the plot path: its ax.stats no longer replace the given stats."""
    assert _plot(tmp_path, {"n": 2}, ax_stats={"r": 0.3}, pass_ax=True) == {
        "n": 2,
        "r": 0.3,
    }


def test_to_plot_stats_table(tmp_path):
    """A table of tests as the stats: a row per comparison."""
    import pandas as pd

    stats = pd.DataFrame({"y": ["a\n(10)", "b"], "P": [0.1, 0.2]})
    assert _plot(tmp_path, stats) == {"a:P": 0.1, "b:P": 0.2}


def test_to_plot_stats_none(tmp_path):
    """None: no stats.yaml."""
    assert _plot(tmp_path, None, ax_stats={"r": 0.3}) is None
