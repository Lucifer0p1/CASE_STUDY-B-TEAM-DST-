"""Simple bar-chart helpers: one blue highlight, grey for everything else,
the finding as the title, and a 'Source: ...' line at the bottom."""

import textwrap

import matplotlib
matplotlib.use("Agg")          # save PNGs without opening a window
import matplotlib.pyplot as plt

BLUE = "#257de0"     # highlight
GREY = "#c4c4c4"     # everything else
TEXT = "#191919"
MUTED = "#666666"


def _style_axes(ax, horizontal):
    """Light, quiet axes so the bars stand out."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=TEXT)
    ax.grid(axis="x" if horizontal else "y", color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)


def _finish(fig, ax, title, source, path):
    """Add the title and source line, then save and close the figure."""
    ax.set_title("\n".join(textwrap.wrap(title, 70)), loc="left",
                 fontsize=13, fontweight="bold", color=TEXT, pad=14)
    fig.text(0.01, 0.01, "\n".join(textwrap.wrap("Source: " + source, 130)),
             fontsize=8, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"  saved {path}")


def bar_chart(labels, values, highlight, title, source, path,
              horizontal=False, value_labels=None, axis_label=""):
    """Plain bar chart. `highlight` is a list of positions to colour blue."""
    labels = [str(l) for l in labels]
    colors = [BLUE if i in highlight else GREY for i in range(len(values))]
    if value_labels is None:
        value_labels = [f"{v:,.1f}" for v in values]

    height = max(4, 0.45 * len(labels) + 1.5) if horizontal else 5
    fig, ax = plt.subplots(figsize=(9, height))
    if horizontal:
        # reverse so the first label is at the top
        bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.6)
        ax.bar_label(bars, labels=value_labels[::-1], padding=4, color=TEXT, fontsize=9)
        ax.set_xlabel(axis_label, color=MUTED)
        ax.margins(x=0.18)
    else:
        bars = ax.bar(labels, values, color=colors, width=0.6)
        ax.bar_label(bars, labels=value_labels, padding=3, color=TEXT, fontsize=10)
        ax.set_ylabel(axis_label, color=MUTED)
        ax.margins(y=0.15)
        if min(values) < 0:
            ax.axhline(0, color=MUTED, linewidth=0.8)
    _style_axes(ax, horizontal)
    _finish(fig, ax, title, source, path)


def paired_bar_chart(groups, grey_values, blue_values, grey_name, blue_name,
                     title, source, path, group_notes=None, axis_label=""):
    """Two bars per group: a grey 'before/design' bar and a blue 'after/peak' bar.

    `group_notes` is optional text written above each pair (e.g. '+35%').
    """
    x = range(len(groups))
    width = 0.36
    fig, ax = plt.subplots(figsize=(9, 5))
    grey_bars = ax.bar([i - width / 2 - 0.01 for i in x], grey_values, width,
                       color=GREY, label=grey_name)
    blue_bars = ax.bar([i + width / 2 + 0.01 for i in x], blue_values, width,
                       color=BLUE, label=blue_name)
    ax.bar_label(grey_bars, labels=[f"{v:,.0f}" for v in grey_values], padding=3, fontsize=9, color=TEXT)
    ax.bar_label(blue_bars, labels=[f"{v:,.0f}" for v in blue_values], padding=3, fontsize=9, color=TEXT)
    if group_notes:
        top = max(max(grey_values), max(blue_values))
        for i, note in zip(x, group_notes):
            ax.text(i, top * 1.14, note, ha="center", fontsize=11, fontweight="bold", color=TEXT)
        ax.set_ylim(0, top * 1.28)
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(g) for g in groups])
    ax.set_ylabel(axis_label, color=MUTED)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=9)
    _style_axes(ax, horizontal=False)
    _finish(fig, ax, title, source, path)
