"""
Statistical Analysis View for the Compression Laboratory GUI.
Visualizes Shannon entropy, byte histograms, autocorrelation, conditional entropy,
and theoretical limits.
"""

from typing import Dict, Any, List
import customtkinter as ctk
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from core.statistics import FileStatistics, analyze_bytes
from visualization.charts import (
    create_histogram_figure,
    create_local_entropy_figure,
    create_autocorrelation_figure
)


class AnalysisView(ctk.CTkFrame):
    def __init__(self, master, get_shared_state, set_shared_state, **kwargs):
        super().__init__(master, **kwargs)
        self.get_shared_state = get_shared_state
        self.set_shared_state = set_shared_state
        self.canvas = None
        self.current_fig = None

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Metric Badges (Top Row)
        self.card_entropy = self._create_metric_card("Shannon Entropy", "0.0000", "bits / symbol", 0)
        self.card_max_entropy = self._create_metric_card("Max Possible H(X)", "8.0000", "bits (256 alphabet)", 1)
        self.card_theo_bound = self._create_metric_card("Theoretical Min", "0 B", "Shannon bound", 2)
        self.card_cond_entropy = self._create_metric_card("Conditional H(X|Y)", "0.0000", "1st order memory", 3)

        # 2. Controls & Chart Selection Bar
        ctrl_bar = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_bar.grid(row=1, column=0, columnspan=4, padx=15, pady=(10, 5), sticky="ew")

        ctk.CTkButton(
            ctrl_bar,
            text="Recompute Analysis",
            width=140,
            command=self.refresh_analysis
        ).pack(side="left", padx=5)

        self.chart_selector = ctk.CTkSegmentedButton(
            ctrl_bar,
            values=["Byte Histogram", "Local Chunk Entropy", "Autocorrelation"],
            command=self._on_chart_changed
        )
        self.chart_selector.set("Byte Histogram")
        self.chart_selector.pack(side="right", padx=5)

        # 3. Chart Container
        self.chart_frame = ctk.CTkFrame(self, corner_radius=10)
        self.chart_frame.grid(row=2, column=0, columnspan=3, padx=(15, 5), pady=10, sticky="nsew")

        # 4. Symbol Frequency & Educational Breakdown Panel (Right Side)
        side_panel = ctk.CTkFrame(self, corner_radius=10)
        side_panel.grid(row=2, column=3, padx=(5, 15), pady=10, sticky="nsew")

        ctk.CTkLabel(side_panel, text="Top Symbols & N-grams", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 5)
        )

        self.table_box = ctk.CTkTextbox(side_panel, font=ctk.CTkFont(family="Consolas", size=10), height=220)
        self.table_box.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(side_panel, text="Theoretical Insight", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 5)
        )
        self.lbl_explanation = ctk.CTkLabel(
            side_panel,
            text=(
                "Shannon's Source Coding Theorem establishes that no lossless algorithm "
                "can compress data to fewer bits per symbol on average than H(X) = -sum p*log2(p).\n\n"
                "If conditional entropy H(X_i | X_{i-1}) < H(X), the data exhibits sequential correlation "
                "which dictionary algorithms (like LZW) or delta transforms can exploit."
            ),
            wraplength=220,
            justify="left",
            font=ctk.CTkFont(size=11)
        )
        self.lbl_explanation.pack(anchor="w", padx=10, pady=5)

    def _create_metric_card(self, title: str, value: str, sub: str, col: int) -> Dict[str, Any]:
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.grid(row=0, column=col, padx=8, pady=(10, 5), sticky="ew")
        lbl_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=11))
        lbl_title.pack(anchor="w", padx=10, pady=(6, 0))
        lbl_val = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=18, weight="bold"))
        lbl_val.pack(anchor="w", padx=10, pady=0)
        lbl_sub = ctk.CTkLabel(frame, text=sub, font=ctk.CTkFont(size=10), text_color="gray")
        lbl_sub.pack(anchor="w", padx=10, pady=(0, 6))
        return {"val": lbl_val, "sub": lbl_sub}

    def refresh_analysis(self):
        data = self.get_shared_state("active_data")
        if data is None or len(data) == 0:
            # Use small demo text if nothing loaded
            data = "Compression Laboratory Sample: The quick brown fox jumps over the lazy dog. 1234567890".encode("utf-8")
            self.set_shared_state("active_data", data)
            self.set_shared_state("active_name", "sample.txt")

        stats = analyze_bytes(data, compute_advanced=True)
        self.set_shared_state("active_stats", stats)

        # Update metric cards
        self.card_entropy["val"].configure(text=f"{stats.shannon_entropy:.4f}")
        self.card_max_entropy["val"].configure(text=f"{stats.max_entropy:.4f}")
        self.card_theo_bound["val"].configure(text=f"{stats.theoretical_min_size_bytes:,.1f} B")
        self.card_cond_entropy["val"].configure(text=f"{stats.conditional_entropy:.4f}")

        # Update table box
        lines = [f"{'Byte':<8} | {'Count':<8} | {'Prob':<8}", "-" * 30]
        for b, count, prob in stats.top_symbols:
            char_rep = f"'{chr(b)}'" if 32 <= b <= 126 else f"0x{b:02X}"
            lines.append(f"{char_rep:<8} | {count:<8} | {prob:.4f}")

        if stats.top_bigrams:
            lines.append("\nTop Bigrams (X, Y):")
            lines.append(f"{'Bigram':<10} | {'Count':<6} | {'Prob':<6}")
            lines.append("-" * 30)
            for (b1, b2), count, prob in stats.top_bigrams[:5]:
                bg_str = f"{chr(b1) if 32 <= b1 <= 126 else '?'}{chr(b2) if 32 <= b2 <= 126 else '?'}"
                lines.append(f"{bg_str:<10} | {count:<6} | {prob:.4f}")

        self.table_box.delete("1.0", "end")
        self.table_box.insert("1.0", "\n".join(lines))

        self._render_current_chart(stats)

    def _on_chart_changed(self, value):
        stats = self.get_shared_state("active_stats")
        if stats:
            self._render_current_chart(stats)

    def _render_current_chart(self, stats: FileStatistics):
        selected = self.chart_selector.get()
        if self.current_fig:
            plt.close(self.current_fig)
        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        if selected == "Byte Histogram":
            fig = create_histogram_figure(stats.byte_frequencies, dark_mode=True)
        elif selected == "Local Chunk Entropy":
            fig = create_local_entropy_figure(stats.chunk_entropies, stats.shannon_entropy, dark_mode=True)
        else:
            fig = create_autocorrelation_figure(stats.autocorrelation, dark_mode=True)

        self.current_fig = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
