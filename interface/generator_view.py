"""
Random Data Generator & Entropy Experiment View.
Allows generating data with precise statistical properties and running automated
entropy-vs-compressibility sweeps.
"""

from typing import List, Dict, Any, Tuple
from pathlib import Path
from tkinter import filedialog, messagebox
import customtkinter as ctk
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from algorithms import get_algorithm
from algorithms.base import AlgorithmId, AlgorithmConfig
from analysis.generator import (
    GenerationMode,
    generate_dataset
)
from core.statistics import analyze_bytes
from visualization.charts import create_entropy_vs_ratio_figure


class GeneratorView(ctk.CTkFrame):
    def __init__(self, master, get_shared_state, set_shared_state, log_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.get_shared_state = get_shared_state
        self.set_shared_state = set_shared_state
        self.log_callback = log_callback
        self.canvas = None
        self.current_fig = None

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Generator Parameters Card (Left)
        gen_card = ctk.CTkFrame(self, corner_radius=10)
        gen_card.grid(row=0, column=0, rowspan=2, padx=(15, 5), pady=10, sticky="nsew")

        ctk.CTkLabel(gen_card, text="Controlled Data Generator", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 5)
        )

        # Mode
        ctk.CTkLabel(gen_card, text="Generation Mode:").pack(anchor="w", padx=15, pady=(5, 2))
        self.mode_select = ctk.CTkComboBox(
            gen_card,
            values=[
                "Controlled Entropy (Target H)",
                "Biased Distribution (Zipf)",
                "Markov Sequence (Persistence)",
                "Uniform Random Bytes",
                "Repeated Pattern",
                "Periodic Waveform"
            ],
            command=self._on_mode_change
        )
        self.mode_select.set("Controlled Entropy (Target H)")
        self.mode_select.pack(fill="x", padx=15, pady=(0, 10))

        # Size & Seed
        size_frame = ctk.CTkFrame(gen_card, fg_color="transparent")
        size_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(size_frame, text="Size (Bytes):").pack(side="left")
        self.size_entry = ctk.CTkEntry(size_frame, width=100)
        self.size_entry.insert(0, "8192")
        self.size_entry.pack(side="right")

        seed_frame = ctk.CTkFrame(gen_card, fg_color="transparent")
        seed_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(seed_frame, text="Random Seed (Optional):").pack(side="left")
        self.seed_entry = ctk.CTkEntry(seed_frame, width=100)
        self.seed_entry.insert(0, "42")
        self.seed_entry.pack(side="right")

        # Dynamic parameter controls
        self.param_title = ctk.CTkLabel(gen_card, text="Target Entropy H(X) [0.1..8.0 bits]:")
        self.param_title.pack(anchor="w", padx=15, pady=(10, 2))

        self.param_slider = ctk.CTkSlider(gen_card, from_=0.2, to=7.9, number_of_steps=77)
        self.param_slider.set(3.5)
        self.param_slider.pack(fill="x", padx=15, pady=2)

        self.param_val_lbl = ctk.CTkLabel(gen_card, text="Value: 3.50")
        self.param_val_lbl.pack(anchor="w", padx=15, pady=(0, 10))
        self.param_slider.configure(command=lambda v: self.param_val_lbl.configure(text=f"Value: {v:.2f}"))

        # Action Buttons
        btn_box = ctk.CTkFrame(gen_card, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=10)

        ctk.CTkButton(
            btn_box,
            text="Generate & Set as Active",
            fg_color="#3A86FF",
            hover_color="#2563EB",
            font=ctk.CTkFont(weight="bold"),
            command=self._generate_single
        ).pack(fill="x", pady=4)

        ctk.CTkButton(
            btn_box,
            text="Save to Disk (.bin)",
            command=self._save_to_disk
        ).pack(fill="x", pady=4)

        # 2. Automated Experiment Card (Right Top)
        exp_card = ctk.CTkFrame(self, corner_radius=10)
        exp_card.grid(row=0, column=1, padx=(5, 15), pady=10, sticky="ew")

        ctk.CTkLabel(exp_card, text="Automated Entropy vs. Compression Sweep", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 5)
        )
        ctk.CTkLabel(
            exp_card,
            text="Sweeps target entropy from 1.0 to 7.8 bits, executes all core algorithms on identical data, and plots actual vs theoretical compression curves.",
            wraplength=400,
            justify="left",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkButton(
            exp_card,
            text="Run Automated Entropy Sweep (6 Points)",
            fg_color="#F72585",
            hover_color="#B5179E",
            font=ctk.CTkFont(weight="bold"),
            command=self._run_entropy_sweep
        ).pack(anchor="w", padx=15, pady=(0, 12))

        # 3. Chart Container (Right Bottom)
        self.chart_frame = ctk.CTkFrame(self, corner_radius=10)
        self.chart_frame.grid(row=1, column=1, padx=(5, 15), pady=(0, 10), sticky="nsew")

    def _on_mode_change(self, mode_str: str):
        if "Controlled" in mode_str:
            self.param_title.configure(text="Target Entropy H(X) [0.2..7.9 bits]:")
            self.param_slider.configure(from_=0.2, to=7.9)
            self.param_slider.set(3.5)
            self.param_val_lbl.configure(text="Value: 3.50")
        elif "Zipf" in mode_str:
            self.param_title.configure(text="Zipf Skewness s [0.0 (Uniform) .. 2.5 (Biased)]:")
            self.param_slider.configure(from_=0.0, to=2.5)
            self.param_slider.set(1.0)
            self.param_val_lbl.configure(text="Value: 1.00")
        elif "Markov" in mode_str:
            self.param_title.configure(text="Persistence Parameter α [0.0 .. 0.98]:")
            self.param_slider.configure(from_=0.0, to=0.98)
            self.param_slider.set(0.85)
            self.param_val_lbl.configure(text="Value: 0.85")
        else:
            self.param_title.configure(text="Noise Rate / Period parameter:")
            self.param_slider.configure(from_=0.0, to=1.0)
            self.param_slider.set(0.05)
            self.param_val_lbl.configure(text="Value: 0.05")

    def _generate_data(self) -> bytes:
        mode_str = self.mode_select.get()
        size = int(self.size_entry.get().strip())
        seed_str = self.seed_entry.get().strip()
        seed = int(seed_str) if seed_str.isdigit() else None
        slider_val = self.param_slider.get()

        if "Controlled" in mode_str:
            return generate_dataset(GenerationMode.CONTROLLED_ENTROPY, size, seed=seed, target_entropy=slider_val)
        elif "Zipf" in mode_str:
            return generate_dataset(GenerationMode.BIASED_ZIPF, size, seed=seed, skew=slider_val)
        elif "Markov" in mode_str:
            return generate_dataset(GenerationMode.MARKOV, size, seed=seed, persistence=slider_val)
        elif "Uniform" in mode_str:
            return generate_dataset(GenerationMode.UNIFORM, size, seed=seed)
        elif "Pattern" in mode_str:
            return generate_dataset(GenerationMode.REPEATED_PATTERN, size, seed=seed, noise_rate=slider_val)
        else:
            return generate_dataset(GenerationMode.PERIODIC, size, seed=seed, period=int(slider_val * 64) + 8)

    def _generate_single(self):
        data = self._generate_data()
        stats = analyze_bytes(data, compute_advanced=True)
        name = f"generated_H{stats.shannon_entropy:.2f}_{len(data)}B.bin"

        self.set_shared_state("active_data", data)
        self.set_shared_state("active_name", name)
        self.set_shared_state("is_archive", False)
        self.set_shared_state("active_stats", stats)

        messagebox.showinfo(
            "Data Generated",
            f"Successfully generated {len(data):,} bytes!\n"
            f"Empirical Shannon Entropy: {stats.shannon_entropy:.4f} bits/symbol\n"
            f"Unique Symbols: {stats.unique_symbols}\n"
            f"Set as active input for Dashboard & Tournament."
        )

    def _save_to_disk(self):
        data = self._generate_data()
        f = filedialog.asksaveasfilename(title="Save Generated File", defaultextension=".bin")
        if f:
            with open(f, "wb") as fl:
                fl.write(data)
            messagebox.showinfo("Saved", f"Wrote {len(data):,} bytes to {Path(f).name}")

    def _run_entropy_sweep(self):
        target_entropies = [1.0, 2.5, 4.0, 5.5, 6.8, 7.8]
        size = 8192

        algos_to_test = [
            ("Huffman", AlgorithmId.HUFFMAN),
            ("Arithmetic", AlgorithmId.ARITHMETIC_STATIC),
            ("Shannon-Fano", AlgorithmId.SHANNON_FANO),
            ("LZW", AlgorithmId.LZW)
        ]

        actual_entropies = []
        ratios_by_algo = {name: [] for name, _ in algos_to_test}

        for target_h in target_entropies:
            data = generate_dataset(GenerationMode.CONTROLLED_ENTROPY, size, seed=100, target_entropy=target_h)
            stats = analyze_bytes(data, compute_advanced=False)
            actual_entropies.append(stats.shannon_entropy)

            for name, algo_id in algos_to_test:
                algo = get_algorithm(algo_id)
                cfg = AlgorithmConfig(algorithm_id=algo_id, block_size=1)
                res = algo.compress(data, cfg)
                total_size = len(res.compressed_bytes) + len(res.model_metadata) + 23
                ratio = len(data) / total_size if total_size > 0 else 0.0
                ratios_by_algo[name].append(ratio)

        # Plot
        if self.current_fig:
            plt.close(self.current_fig)
        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        fig = create_entropy_vs_ratio_figure(actual_entropies, ratios_by_algo, dark_mode=True)
        self.current_fig = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
