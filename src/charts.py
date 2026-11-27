import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE = "#257de0"
GREY = "#c4c4c4"
DARK = "#191919"
LIGHT = "#666666"


def finish_and_save(fig, ax, title, source, filename, horizontal=False):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if horizontal:
        ax.grid(axis="x", color="#e6e6e6")
    else:
        ax.grid(axis="y", color="#e6e6e6")
    ax.set_axisbelow(True)

    ax.set_title(textwrap.fill(title, 70), loc="left", fontsize=13, fontweight="bold", color=DARK, pad=14)
    fig.text(0.01, 0.01, textwrap.fill("Source: " + source, 130), fontsize=8, color=LIGHT)

    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(filename, dpi=150, facecolor="white")
    plt.close(fig)
    print("Saved", filename)


def bar_chart(labels, values, highlight, title, source, filename,
              horizontal=False, value_labels=None, axis_label=""):
    labels = [str(x) for x in labels]
    values = list(values)

    colors = []
    for i in range(len(values)):
        if i in highlight:
            colors.append(BLUE)
        else:
            colors.append(GREY)

    if value_labels is None:
        value_labels = [f"{v:.1f}" for v in values]

    if horizontal:
        height = max(4, 0.45 * len(labels) + 1.5)
        fig, ax = plt.subplots(figsize=(9, height))
        # barh draws bottom-up, so flip everything to keep the first item on top
        bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.6)
        ax.bar_label(bars, labels=value_labels[::-1], padding=4, fontsize=9)
        ax.set_xlabel(axis_label, color=LIGHT)
        ax.margins(x=0.18)
    else:
        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.bar(labels, values, color=colors, width=0.6)
        ax.bar_label(bars, labels=value_labels, padding=3)
        ax.set_ylabel(axis_label, color=LIGHT)
        ax.margins(y=0.15)
        ax.axhline(0, color=LIGHT, linewidth=0.8)

    finish_and_save(fig, ax, title, source, filename, horizontal)


def paired_bar_chart(groups, grey_vals, blue_vals, grey_label, blue_label,
                     title, source, filename, notes, axis_label=""):
    x = list(range(len(groups)))
    w = 0.36

    fig, ax = plt.subplots(figsize=(9, 5))
    b1 = ax.bar([i - 0.19 for i in x], grey_vals, w, color=GREY, label=grey_label)
    b2 = ax.bar([i + 0.19 for i in x], blue_vals, w, color=BLUE, label=blue_label)
    ax.bar_label(b1, fmt="{:,.0f}", padding=3, fontsize=9)
    ax.bar_label(b2, fmt="{:,.0f}", padding=3, fontsize=9)

    # write the ratio / % change above each pair
    top = max(max(grey_vals), max(blue_vals))
    for i in x:
        ax.text(i, top * 1.14, notes[i], ha="center", fontsize=11, fontweight="bold")
    ax.set_ylim(0, top * 1.28)

    ax.set_xticks(x)
    ax.set_xticklabels([str(g) for g in groups])
    ax.set_ylabel(axis_label, color=LIGHT)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=9)

    finish_and_save(fig, ax, title, source, filename)
