"""
Chart generation module for statistical profiles and benchmarking tournament results.
Renders Matplotlib Figures styled for dark or light laboratory UI themes.
"""

from typing import Dict, List, Optional, Any
import matplotlib
# Use TkAgg or Agg depending on context
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np


def apply_theme(fig: Figure, ax: plt.Axes, dark_mode: bool = True) -> None:
    """Applies a sleek modern scientific styling to Matplotlib figures."""
    if dark_mode:
        bg_color = "#1E1E1E"
        card_color = "#252526"
        text_color = "#E0E0E0"
        grid_color = "#333333"
    else:
        bg_color = "#F8F9FA"
        card_color = "#FFFFFF"
        text_color = "#212529"
        grid_color = "#E9ECEF"

    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(card_color)
    ax.tick_params(colors=text_color, labelsize=9)
    ax.xaxis.label.set_color(text_color)
    ax.yaxis.label.set_color(text_color)
    ax.title.set_color(text_color)
    for spine in ax.spines.values():
        spine.set_color(grid_color)
    ax.grid(True, linestyle="--", alpha=0.5, color=grid_color)


def create_histogram_figure(byte_frequencies: Dict[int, int], dark_mode: bool = True) -> Figure:
    """Creates a 256-byte frequency histogram figure."""
    fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=100)
    apply_theme(fig, ax, dark_mode)

    x = np.arange(256)
    y = np.array([byte_frequencies.get(i, 0) for i in range(256)])

    # Color gradient based on frequency
    accent_color = "#4CC9F0" if dark_mode else "#0077B6"
    ax.bar(x, y, width=1.0, color=accent_color, edgecolor="none", alpha=0.85)

    ax.set_xlim(-1, 256)
    ax.set_xlabel("Byte Value (0..255)")
    ax.set_ylabel("Frequency Count")
    ax.set_title("Byte Frequency Distribution (0x00 - 0xFF)", fontsize=11, fontweight="bold")
    fig.tight_layout()
    return fig


def create_local_entropy_figure(
    chunk_entropies: List[float],
    overall_entropy: float,
    dark_mode: bool = True
) -> Figure:
    """Creates a local chunk entropy profile line chart across the file."""
    fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=100)
    apply_theme(fig, ax, dark_mode)

    if not chunk_entropies:
        chunk_entropies = [0.0]

    x = np.arange(len(chunk_entropies))
    y = np.array(chunk_entropies)

    line_color = "#7209B7" if dark_mode else "#560BAD"
    ax.plot(x, y, color=line_color, linewidth=2, marker="o", markersize=3, label="Local Chunk H(X)")
    ax.axhline(
        overall_entropy,
        color="#F72585",
        linestyle="--",
        linewidth=1.5,
        label=f"Overall H(X) = {overall_entropy:.2f}"
    )

    ax.set_ylim(-0.2, 8.2)
    ax.set_xlabel("File Chunk Index")
    ax.set_ylabel("Shannon Entropy (bits/symbol)")
    ax.set_title("Local Entropy Variation Across File", fontsize=11, fontweight="bold")
    ax.legend(facecolor="#252526" if dark_mode else "#FFFFFF", edgecolor="none", labelcolor="#E0E0E0" if dark_mode else "#212529")
    fig.tight_layout()
    return fig


def create_autocorrelation_figure(autocorr: List[float], dark_mode: bool = True) -> Figure:
    """Plots autocorrelation across lags 1..32."""
    fig, ax = plt.subplots(figsize=(6.5, 3.0), dpi=100)
    apply_theme(fig, ax, dark_mode)

    lags = np.arange(1, len(autocorr) + 1)
    values = np.array(autocorr)

    bar_color = "#3A86FF" if dark_mode else "#023E8A"
    ax.bar(lags, values, color=bar_color, width=0.6, alpha=0.85)
    ax.axhline(0, color="#888888", linewidth=1)

    ax.set_ylim(-1.05, 1.05)
    ax.set_xlabel("Lag k (Bytes)")
    ax.set_ylabel("Autocorrelation ρ(k)")
    ax.set_title("Byte-Level Autocorrelation (Lags 1..32)", fontsize=11, fontweight="bold")
    fig.tight_layout()
    return fig


def create_tournament_bar_figure(records: List[Any], dark_mode: bool = True) -> Figure:
    """Generates comparison bar chart of total compressed sizes with original baseline."""
    fig, ax = plt.subplots(figsize=(7.5, 3.8), dpi=100)
    apply_theme(fig, ax, dark_mode)

    if not records:
        ax.text(0.5, 0.5, "No tournament data", ha="center", va="center", color="#888")
        return fig

    names = [r.algorithm_name for r in records]
    sizes = [r.compressed_container_size for r in records]
    orig_size = records[0].original_size

    y_pos = np.arange(len(names))
    colors = ["#4361EE", "#4CC9F0", "#3F37C9", "#7209B7", "#B5179E", "#F72585", "#4895EF"]
    bar_colors = [colors[i % len(colors)] for i in range(len(names))]

    bars = ax.barh(y_pos, sizes, color=bar_colors, alpha=0.85, height=0.55)
    ax.axvline(orig_size, color="#FF4D6D", linestyle="--", linewidth=1.8, label=f"Original Size ({orig_size} B)")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("Total File Size (Bytes, Including Headers & Models)")
    ax.set_title("Tournament Size Comparison (Smaller is Better)", fontsize=11, fontweight="bold")
    ax.legend(facecolor="#252526" if dark_mode else "#FFFFFF", edgecolor="none", labelcolor="#E0E0E0" if dark_mode else "#212529")

    # Add data labels
    for bar in bars:
        w = bar.get_width()
        ax.text(
            w + (orig_size * 0.02 if orig_size > 0 else 5),
            bar.get_y() + bar.get_height() / 2,
            f"{int(w)} B",
            va="center",
            ha="left",
            fontsize=8,
            color="#E0E0E0" if dark_mode else "#212529"
        )

    fig.tight_layout()
    return fig


def create_entropy_vs_ratio_figure(
    entropy_values: List[float],
    ratios_by_algo: Dict[str, List[float]],
    dark_mode: bool = True
) -> Figure:
    """Plots Entropy vs Compression Ratio curves for different algorithms."""
    fig, ax = plt.subplots(figsize=(7.0, 3.6), dpi=100)
    apply_theme(fig, ax, dark_mode)

    colors = ["#4CC9F0", "#F72585", "#7209B7", "#3A86FF", "#4BB543"]
    for i, (name, ratios) in enumerate(ratios_by_algo.items()):
        color = colors[i % len(colors)]
        ax.plot(
            entropy_values,
            ratios,
            marker="o",
            linewidth=2,
            label=name,
            color=color,
            alpha=0.9
        )

    # Theoretical Shannon bound line: ratio = 8.0 / H(X)
    theo_x = [e for e in entropy_values if e > 0.1]
    theo_y = [8.0 / e for e in theo_x]
    ax.plot(theo_x, theo_y, linestyle=":", color="#FFD166", linewidth=1.8, label="Shannon Bound (8 / H)")

    ax.set_xlabel("Empirical Source Entropy H(X) [bits]")
    ax.set_ylabel("Compression Ratio (Original / Total Compressed)")
    ax.set_title("Source Entropy vs. Compression Ratio", fontsize=11, fontweight="bold")
    ax.legend(facecolor="#252526" if dark_mode else "#FFFFFF", edgecolor="none", labelcolor="#E0E0E0" if dark_mode else "#212529")
    fig.tight_layout()
    return fig
