"""
Educational Compression Laboratory View.
Provides deep-dive step-by-step transparency, tree visualizers,
codeword dictionaries, and interval subdivision traces.
"""

from collections import Counter
from typing import Dict, List, Any, Tuple
import customtkinter as ctk
import tkinter as tk

from algorithms import get_algorithm
from algorithms.base import AlgorithmId, AlgorithmConfig
from algorithms.huffman import (
    build_huffman_tree,
    generate_codewords,
    render_ascii_tree,
    chunk_data_into_blocks
)
from algorithms.shannon_fano import partition_symbols
from visualization.tree_visualizer import (
    render_shannon_fano_partitions,
    render_arithmetic_interval_steps,
    format_symbol
)


class LabView(ctk.CTkFrame):
    def __init__(self, master, get_shared_state, set_shared_state, **kwargs):
        super().__init__(master, **kwargs)
        self.get_shared_state = get_shared_state
        self.set_shared_state = set_shared_state

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Configuration & Input Panel (Top)
        top_panel = ctk.CTkFrame(self, corner_radius=10)
        top_panel.grid(row=0, column=0, columnspan=2, padx=15, pady=(10, 5), sticky="ew")
        top_panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top_panel, text="Educational Experiment Setup", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=4, padx=15, pady=(10, 5), sticky="w"
        )

        ctk.CTkLabel(top_panel, text="Sample Text / Input:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.sample_input = ctk.CTkEntry(top_panel, placeholder_text="Type custom text e.g. 'ABRACADABRA'...")
        self.sample_input.insert(0, "ABRACADABRA_TOBEORNOTTOBE")
        self.sample_input.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(
            top_panel,
            text="Use Active File Data",
            width=150,
            command=self._use_active_file
        ).grid(row=1, column=3, padx=15, pady=5)

        # Controls row
        ctrl_frame = ctk.CTkFrame(top_panel, fg_color="transparent")
        ctrl_frame.grid(row=2, column=0, columnspan=4, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(ctrl_frame, text="Algorithm:").pack(side="left", padx=(0, 10))
        self.algo_select = ctk.CTkComboBox(
            ctrl_frame,
            values=["Huffman", "Shannon-Fano", "Arithmetic (Static)", "Arithmetic (Adaptive)", "LZW", "RLE"],
            width=180
        )
        self.algo_select.set("Huffman")
        self.algo_select.pack(side="left", padx=5)

        ctk.CTkLabel(ctrl_frame, text="Block Size:").pack(side="left", padx=(15, 10))
        self.bs_select = ctk.CTkSegmentedButton(ctrl_frame, values=["1 Byte", "2 Bytes", "3 Bytes"])
        self.bs_select.set("1 Byte")
        self.bs_select.pack(side="left", padx=5)

        ctk.CTkButton(
            ctrl_frame,
            text="Step Through & Visualize",
            fg_color="#7209B7",
            hover_color="#560BAD",
            font=ctk.CTkFont(weight="bold"),
            command=self._run_inspection
        ).pack(side="right", padx=5)

        # 2. Results Header Card
        self.stats_card = ctk.CTkFrame(self, corner_radius=10)
        self.stats_card.grid(row=1, column=0, columnspan=2, padx=15, pady=5, sticky="ew")
        self.stats_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.lbl_orig = ctk.CTkLabel(self.stats_card, text="Original: 0 Bytes", font=ctk.CTkFont(weight="bold"))
        self.lbl_orig.grid(row=0, column=0, padx=10, pady=8)
        self.lbl_comp = ctk.CTkLabel(self.stats_card, text="Total: 0 Bytes", font=ctk.CTkFont(weight="bold"))
        self.lbl_comp.grid(row=0, column=1, padx=10, pady=8)
        self.lbl_ratio = ctk.CTkLabel(self.stats_card, text="Ratio: 0.00x", font=ctk.CTkFont(weight="bold"))
        self.lbl_ratio.grid(row=0, column=2, padx=10, pady=8)
        self.lbl_meta = ctk.CTkLabel(self.stats_card, text="Model/Header: 0 Bytes", font=ctk.CTkFont(weight="bold"))
        self.lbl_meta.grid(row=0, column=3, padx=10, pady=8)

        # 3. Main Display Split (Left: Structure / Tree, Right: Trace & Codewords)
        self.left_box_frame = ctk.CTkFrame(self, corner_radius=10)
        self.left_box_frame.grid(row=2, column=0, padx=(15, 5), pady=10, sticky="nsew")

        ctk.CTkLabel(
            self.left_box_frame,
            text="Internal Model & Structure (Tree / Partitions / Intervals)",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.structure_text = ctk.CTkTextbox(
            self.left_box_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none"
        )
        self.structure_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.right_box_frame = ctk.CTkFrame(self, corner_radius=10)
        self.right_box_frame.grid(row=2, column=1, padx=(5, 15), pady=10, sticky="nsew")

        ctk.CTkLabel(
            self.right_box_frame,
            text="Step-by-Step Execution Trace & Codewords",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.trace_text = ctk.CTkTextbox(
            self.right_box_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none"
        )
        self.trace_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _use_active_file(self):
        data = self.get_shared_state("active_data")
        name = self.get_shared_state("active_name") or "active_data"
        if data:
            preview = data[:64].decode("latin1", errors="replace")
            self.sample_input.delete(0, "end")
            self.sample_input.insert(0, preview)
        else:
            self.sample_input.delete(0, "end")
            self.sample_input.insert(0, "COMPRESSION_LABORATORY_RESEARCH")

    def _run_inspection(self):
        text_val = self.sample_input.get()
        data = text_val.encode("utf-8")
        if not data:
            return

        algo_name = self.algo_select.get()
        bs_str = self.bs_select.get()
        block_size = int(bs_str.split()[0])

        mapping = {
            "Huffman": AlgorithmId.HUFFMAN,
            "Shannon-Fano": AlgorithmId.SHANNON_FANO,
            "Arithmetic (Static)": AlgorithmId.ARITHMETIC_STATIC,
            "Arithmetic (Adaptive)": AlgorithmId.ARITHMETIC_ADAPTIVE,
            "LZW": AlgorithmId.LZW,
            "RLE": AlgorithmId.RLE
        }
        algo_id = mapping.get(algo_name, AlgorithmId.HUFFMAN)
        algo = get_algorithm(algo_id)

        cfg = AlgorithmConfig(algorithm_id=algo_id, block_size=block_size)
        res = algo.compress(data, cfg, record_trace=True, max_traces=150)

        # Update stats
        total_size = len(res.compressed_bytes) + len(res.model_metadata) + 23
        ratio = len(data) / total_size if total_size > 0 else 0.0

        self.lbl_orig.configure(text=f"Original: {len(data)} B")
        self.lbl_comp.configure(text=f"Total: {total_size} B")
        self.lbl_ratio.configure(text=f"Ratio: {ratio:.3f}x")
        self.lbl_meta.configure(text=f"Model/Header: {len(res.model_metadata)} B")

        # Clear text areas
        self.structure_text.delete("1.0", "end")
        self.trace_text.delete("1.0", "end")

        # Populate Structure and Traces according to algorithm
        if algo_id == AlgorithmId.HUFFMAN:
            blocks = chunk_data_into_blocks(data, block_size)
            freq = Counter(blocks)
            root = build_huffman_tree(freq)
            codewords = generate_codewords(root)

            ascii_tree = render_ascii_tree(root, max_depth=10)
            self.structure_text.insert("end", f"=== Deterministic Huffman Tree (Block Size = {block_size}) ===\n\n")
            self.structure_text.insert("end", ascii_tree)

            self.trace_text.insert("end", "=== Huffman Codeword Dictionary ===\n")
            self.trace_text.insert("end", f"{'Symbol':<12} | {'Freq':<6} | {'Bits':<5} | Codeword\n")
            self.trace_text.insert("end", "-" * 42 + "\n")
            for sym, code in sorted(codewords.items(), key=lambda x: (len(x[1]), x[0])):
                self.trace_text.insert("end", f"{format_symbol(sym):<12} | {freq[sym]:<6} | {len(code):<5} | {code}\n")

            self.trace_text.insert("end", "\n=== Execution Trace ===\n")
            for tr in res.traces:
                self.trace_text.insert("end", f"Step {tr.step_num}: {tr.description}\n")

        elif algo_id == AlgorithmId.SHANNON_FANO:
            blocks = chunk_data_into_blocks(data, block_size)
            freq = Counter(blocks)
            sorted_items = sorted(freq.items(), key=lambda x: (-x[1], x[0]))

            partitions = []
            codewords = partition_symbols(sorted_items, partitions)

            part_text = render_shannon_fano_partitions(partitions)
            self.structure_text.insert("end", f"=== Shannon-Fano Partition Hierarchy (BS = {block_size}) ===\n\n")
            self.structure_text.insert("end", part_text)

            self.trace_text.insert("end", "=== Shannon-Fano Codebook ===\n")
            self.trace_text.insert("end", f"{'Symbol':<12} | {'Freq':<6} | {'Bits':<5} | Codeword\n")
            self.trace_text.insert("end", "-" * 42 + "\n")
            for sym, code in sorted(codewords.items(), key=lambda x: (len(x[1]), x[0])):
                self.trace_text.insert("end", f"{format_symbol(sym):<12} | {freq[sym]:<6} | {len(code):<5} | {code}\n")

            self.trace_text.insert("end", "\n=== Execution Trace ===\n")
            for tr in res.traces:
                self.trace_text.insert("end", f"Step {tr.step_num}: {tr.description}\n")

        elif algo_id in (AlgorithmId.ARITHMETIC_STATIC, AlgorithmId.ARITHMETIC_ADAPTIVE):
            self.structure_text.insert("end", f"=== Arithmetic Coding Precision & Bounds ===\n\n")
            self.structure_text.insert("end", f"Precision: 32-bit Integer Arithmetic\n")
            self.structure_text.insert("end", f"Initial Interval: [0x00000000, 0xFFFFFFFF]\n")
            self.structure_text.insert("end", f"Half: 0x80000000 | 1st Qtr: 0x40000000 | 3rd Qtr: 0xC0000000\n\n")
            self.structure_text.insert("end", render_arithmetic_interval_steps(res.traces, max_steps=25))

            self.trace_text.insert("end", "=== Execution Steps & Renormalization Traces ===\n")
            for tr in res.traces:
                self.trace_text.insert("end", f"Step {tr.step_num}: {tr.description}\n")

        elif algo_id == AlgorithmId.LZW:
            self.structure_text.insert("end", "=== LZW Dictionary Evolution ===\n\n")
            self.structure_text.insert("end", f"Initial Alphabet: 256 byte literals (codes 0..255)\n")
            self.structure_text.insert("end", f"Total intermediate strings recorded: {len(res.traces)}\n\n")
            for tr in res.traces[:30]:
                self.structure_text.insert("end", f"[{tr.step_num}] {tr.description}\n")

            self.trace_text.insert("end", "=== Output 16-bit Code Stream ===\n")
            for tr in res.traces:
                self.trace_text.insert("end", f"Code {tr.codeword} for string {tr.symbol!r}\n")

        elif algo_id == AlgorithmId.RLE:
            self.structure_text.insert("end", "=== PackBits Run-Length Encoding ===\n\n")
            self.structure_text.insert("end", "Literal runs: 0..127 (copied directly)\n")
            self.structure_text.insert("end", "Repeated runs: 129..255 (repeated 257-n times)\n")
            self.trace_text.insert("end", f"Input: {len(data)} raw bytes -> Output: {len(res.compressed_bytes)} bytes\n")
