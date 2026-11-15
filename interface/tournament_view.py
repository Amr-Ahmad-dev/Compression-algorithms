"""
Compression Tournament and Benchmarking View.
Executes fair multi-algorithm benchmarking tournaments with real container sizing,
integrity verification, ranking metrics, and CSV/JSON reporting.
"""

from typing import List, Dict, Any
from pathlib import Path
from tkinter import filedialog, messagebox
import customtkinter as ctk
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from algorithms.base import AlgorithmId, AlgorithmConfig
from analysis.benchmark import TournamentRunner, TournamentEntry, BenchmarkRecord
from visualization.charts import create_tournament_bar_figure


class TournamentView(ctk.CTkFrame):
    def __init__(self, master, get_shared_state, set_shared_state, log_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.get_shared_state = get_shared_state
        self.set_shared_state = set_shared_state
        self.log_callback = log_callback
        self.runner = TournamentRunner()
        self.canvas = None
        self.current_fig = None

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Competitor Selection Card (Top)
        top_card = ctk.CTkFrame(self, corner_radius=10)
        top_card.grid(row=0, column=0, columnspan=2, padx=15, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(top_card, text="Tournament Competitors & Configuration", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 5)
        )

        checks_frame = ctk.CTkFrame(top_card, fg_color="transparent")
        checks_frame.pack(fill="x", padx=15, pady=5)

        self.checks = {}
        competitors_list = [
            ("Huffman (Byte)", AlgorithmId.HUFFMAN, 1, True),
            ("Huffman (BS=2)", AlgorithmId.HUFFMAN, 2, True),
            ("Huffman (BS=4)", AlgorithmId.HUFFMAN, 4, False),
            ("Arithmetic (Static)", AlgorithmId.ARITHMETIC_STATIC, 1, True),
            ("Arithmetic (Adaptive)", AlgorithmId.ARITHMETIC_ADAPTIVE, 1, True),
            ("Shannon-Fano", AlgorithmId.SHANNON_FANO, 1, True),
            ("LZW", AlgorithmId.LZW, 1, True),
            ("RLE", AlgorithmId.RLE, 1, True),
            ("Delta + Huffman", AlgorithmId.DELTA_HUFFMAN, 1, True),
        ]

        # 3 columns of checkboxes
        col_frames = [ctk.CTkFrame(checks_frame, fg_color="transparent") for _ in range(3)]
        for i, cf in enumerate(col_frames):
            cf.pack(side="left", fill="both", expand=True)

        for idx, (label, algo_id, bs, default_val) in enumerate(competitors_list):
            cf = col_frames[idx % 3]
            var = ctk.BooleanVar(value=default_val)
            cb = ctk.CTkCheckBox(cf, text=label, variable=var)
            cb.pack(anchor="w", padx=5, pady=3)
            self.checks[label] = (var, algo_id, bs)

        # Action row
        act_row = ctk.CTkFrame(top_card, fg_color="transparent")
        act_row.pack(fill="x", padx=15, pady=(5, 12))

        ctk.CTkButton(
            act_row,
            text="Run Tournament",
            fg_color="#F72585",
            hover_color="#B5179E",
            font=ctk.CTkFont(weight="bold"),
            command=self._run_tournament
        ).pack(side="left", padx=5)

        ctk.CTkButton(act_row, text="Export CSV", width=100, command=self._export_csv).pack(side="right", padx=5)
        ctk.CTkButton(act_row, text="Export JSON", width=100, command=self._export_json).pack(side="right", padx=5)

        # 2. Winner Banner
        self.winner_banner = ctk.CTkLabel(
            self,
            text="Select competitors and press 'Run Tournament' to benchmark.",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E5E7EB", "#2D3748"),
            corner_radius=6,
            height=32
        )
        self.winner_banner.grid(row=1, column=0, columnspan=2, padx=15, pady=5, sticky="ew")

        # 3. Split Display (Left: Results Table, Right: Matplotlib Chart)
        table_frame = ctk.CTkFrame(self, corner_radius=10)
        table_frame.grid(row=2, column=0, padx=(15, 5), pady=10, sticky="nsew")

        ctk.CTkLabel(table_frame, text="Tournament Standings & Audit Table", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 5)
        )

        self.table_box = ctk.CTkTextbox(table_frame, font=ctk.CTkFont(family="Consolas", size=10), wrap="none")
        self.table_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.chart_frame = ctk.CTkFrame(self, corner_radius=10)
        self.chart_frame.grid(row=2, column=1, padx=(5, 15), pady=10, sticky="nsew")

    def _run_tournament(self):
        data = self.get_shared_state("active_data")
        name = self.get_shared_state("active_name") or "dataset"
        if data is None or len(data) == 0:
            # Fallback to realistic benchmark text
            data = ("Information theory and data compression research tournament dataset. "
                    "Testing Huffman, Arithmetic, Shannon-Fano, LZW, and RLE on identical bytes! " * 20).encode("utf-8")
            self.set_shared_state("active_data", data)
            self.set_shared_state("active_name", "benchmark_sample.txt")
            name = "benchmark_sample.txt"

        selected_entries: List[TournamentEntry] = []
        for label, (var, algo_id, bs) in self.checks.items():
            if var.get():
                cfg = AlgorithmConfig(algorithm_id=algo_id, block_size=bs)
                selected_entries.append(TournamentEntry(algorithm_id=algo_id, name=label, config=cfg))

        if not selected_entries:
            messagebox.showwarning("Warning", "Please select at least one competitor algorithm.")
            return

        self.winner_banner.configure(text=f"Running tournament on '{name}' ({len(data):,} bytes)...")
        self.update_idletasks()

        records = self.runner.run_single_competition(data, name, selected_entries)

        # Find winners
        best_size = min(records, key=lambda r: r.compressed_container_size)
        best_speed = min(records, key=lambda r: (r.compression_time_ms + r.decompression_time_ms))

        self.winner_banner.configure(
            text=f"🏆 Size Champion: {best_size.algorithm_name} ({best_size.compressed_container_size:,} B, {best_size.compression_ratio:.2f}x) | ⚡ Speed Champion: {best_speed.algorithm_name} ({(best_speed.compression_time_ms + best_speed.decompression_time_ms):.1f}ms)"
        )

        # Build Table Display
        lines = [
            f"{'Rank':<4} | {'Algorithm':<22} | {'Total Size':<10} | {'Ratio':<7} | {'Saving':<7} | {'Comp(ms)':<8} | {'Decomp(ms)':<10} | {'Integrity'}",
            "-" * 95
        ]

        for r in sorted(records, key=lambda x: x.rank_size):
            integ_str = "✓ EXACT" if r.integrity_verified else "✗ FAILED"
            lines.append(
                f"#{r.rank_size:<3} | {r.algorithm_name:<22} | {r.compressed_container_size:<10} | "
                f"{r.compression_ratio:<7.2f} | {r.space_saving_percent:<6.1f}% | "
                f"{r.compression_time_ms:<8.1f} | {r.decompression_time_ms:<10.1f} | {integ_str}"
            )

        self.table_box.delete("1.0", "end")
        self.table_box.insert("1.0", "\n".join(lines))

        # Update Chart
        if self.current_fig:
            plt.close(self.current_fig)
        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        fig = create_tournament_bar_figure(records, dark_mode=True)
        self.current_fig = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def _export_csv(self):
        f = filedialog.asksaveasfilename(title="Export CSV Results", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if f:
            self.runner.export_to_csv(f)
            messagebox.showinfo("Export Successful", f"Saved {len(self.runner.records)} records to {Path(f).name}")

    def _export_json(self):
        f = filedialog.asksaveasfilename(title="Export JSON Results", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if f:
            self.runner.export_to_json(f)
            messagebox.showinfo("Export Successful", f"Saved {len(self.runner.records)} records to {Path(f).name}")
