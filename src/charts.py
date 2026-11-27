import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE = "#257de0"
GREY = "#c4c4c4"
TEXT = "#191919"
MUTED = "#666666"


def save(fig, ax, title, source, path, horizontal=False):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x" if horizontal else "y", color="#e6e6e6")
    ax.set_axisbelow(True)
    ax.set_title(textwrap.fill(title, 70), loc="left", fontsize=13, fontweight="bold", color=TEXT, pad=14)
    fig.text(0.01, 0.01, textwrap.fill("Source: " + source, 130), fontsize=8, color=MUTED)
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"saved {path}")


def bar_chart(labels, values, highlight, title, source, path,
              horizontal=False, value_labels=None, axis_label=""):
    labels = [str(l) for l in labels]
    values = list(values)
    colors = [BLUE if i in highlight else GREY for i in range(len(values))]
    value_labels = value_labels or [f"{v:,.1f}" for v in values]

    if horizontal:
        fig, ax = plt.subplots(figsize=(9, max(4, 0.45 * len(labels) + 1.5)))
        bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.6)
        ax.bar_label(bars, labels=value_labels[::-1], padding=4, fontsize=9)
        ax.set_xlabel(axis_label, color=MUTED)
        ax.margins(x=0.18)
    else:
        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.bar(labels, values, color=colors, width=0.6)
        ax.bar_label(bars, labels=value_labels, padding=3)
        ax.set_ylabel(axis_label, color=MUTED)
        ax.margins(y=0.15)
        ax.axhline(0, color=MUTED, linewidth=0.8)
    save(fig, ax, title, source, path, horizontal)


def paired_bar_chart(groups, grey_values, blue_values, grey_name, blue_name,
                     title, source, path, notes, axis_label=""):
    x = range(len(groups))
    fig, ax = plt.subplots(figsize=(9, 5))
    grey_bars = ax.bar([i - 0.19 for i in x], grey_values, 0.36, color=GREY, label=grey_name)
    blue_bars = ax.bar([i + 0.19 for i in x], blue_values, 0.36, color=BLUE, label=blue_name)
    ax.bar_label(grey_bars, fmt="{:,.0f}", padding=3, fontsize=9)
    ax.bar_label(blue_bars, fmt="{:,.0f}", padding=3, fontsize=9)

    top = max(max(grey_values), max(blue_values))
    for i, note in zip(x, notes):
        ax.text(i, top * 1.14, note, ha="center", fontsize=11, fontweight="bold")
    ax.set_ylim(0, top * 1.28)
    ax.set_xticks(list(x), [str(g) for g in groups])
    ax.set_ylabel(axis_label, color=MUTED)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=9)
    save(fig, ax, title, source, path)
