"""
Dashboard View for the Compression Laboratory GUI.
Provides quick file/folder selection, metadata overview, and rapid compression/decompression actions.
"""

import os
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from algorithms import ALGORITHM_REGISTRY, get_algorithm
from algorithms.base import AlgorithmId, AlgorithmConfig
from core.container import build_container, decompress_container, pack_directory, unpack_directory
from core.statistics import analyze_bytes


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, get_shared_state, set_shared_state, log_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.get_shared_state = get_shared_state
        self.set_shared_state = set_shared_state
        self.log_callback = log_callback

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure((0, 1), weight=1)

        # 1. Source Selection Card
        sel_card = ctk.CTkFrame(self, corner_radius=10)
        sel_card.grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        sel_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(sel_card, text="Target Input Selection", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=3, padx=15, pady=(10, 5), sticky="w"
        )

        self.path_entry = ctk.CTkEntry(sel_card, placeholder_text="Select a file or directory...")
        self.path_entry.grid(row=1, column=0, columnspan=2, padx=15, pady=10, sticky="ew")

        btn_box = ctk.CTkFrame(sel_card, fg_color="transparent")
        btn_box.grid(row=1, column=2, padx=15, pady=10, sticky="e")

        ctk.CTkButton(btn_box, text="Browse File", width=100, command=self._browse_file).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text="Browse Folder", width=110, command=self._browse_folder).pack(side="left", padx=5)

        # 2. File / Folder Information Card
        self.info_card = ctk.CTkFrame(self, corner_radius=10)
        self.info_card.grid(row=1, column=0, padx=15, pady=10, sticky="nsew")

        ctk.CTkLabel(self.info_card, text="Source Properties", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 5)
        )
        self.lbl_info_type = ctk.CTkLabel(self.info_card, text="Type: None", anchor="w")
        self.lbl_info_type.pack(anchor="w", padx=15, pady=2)
        self.lbl_info_size = ctk.CTkLabel(self.info_card, text="Size: 0 Bytes", anchor="w")
        self.lbl_info_size.pack(anchor="w", padx=15, pady=2)
        self.lbl_info_entropy = ctk.CTkLabel(self.info_card, text="Shannon Entropy: N/A", anchor="w")
        self.lbl_info_entropy.pack(anchor="w", padx=15, pady=2)
        self.lbl_info_bound = ctk.CTkLabel(self.info_card, text="Theoretical Min (Shannon): N/A", anchor="w")
        self.lbl_info_bound.pack(anchor="w", padx=15, pady=2)

        # 3. Quick Actions Card
        act_card = ctk.CTkFrame(self, corner_radius=10)
        act_card.grid(row=1, column=1, padx=15, pady=10, sticky="nsew")

        ctk.CTkLabel(act_card, text="Quick Compression & Decompression", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 5)
        )

        algo_frame = ctk.CTkFrame(act_card, fg_color="transparent")
        algo_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(algo_frame, text="Algorithm:").pack(side="left", padx=(0, 10))
        self.algo_dropdown = ctk.CTkComboBox(
            algo_frame,
            values=[
                "Huffman",
                "Arithmetic (Static)",
                "Arithmetic (Adaptive)",
                "Shannon-Fano",
                "LZW",
                "RLE",
                "Delta + Huffman"
            ],
            width=200
        )
        self.algo_dropdown.set("Huffman")
        self.algo_dropdown.pack(side="left")

        bs_frame = ctk.CTkFrame(act_card, fg_color="transparent")
        bs_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(bs_frame, text="Block Size:").pack(side="left", padx=(0, 10))
        self.block_size_opt = ctk.CTkSegmentedButton(bs_frame, values=["1 Byte", "2 Bytes", "3 Bytes", "4 Bytes"])
        self.block_size_opt.set("1 Byte")
        self.block_size_opt.pack(side="left")

        btn_row = ctk.CTkFrame(act_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=15)
        ctk.CTkButton(
            btn_row,
            text="Compress to .clab",
            fg_color="#3A86FF",
            hover_color="#2563EB",
            font=ctk.CTkFont(weight="bold"),
            command=self._do_compress
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(
            btn_row,
            text="Decompress .clab",
            fg_color="#10B981",
            hover_color="#059669",
            font=ctk.CTkFont(weight="bold"),
            command=self._do_decompress
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))

        # 4. Activity Log Card
        log_card = ctk.CTkFrame(self, corner_radius=10)
        log_card.grid(row=2, column=0, columnspan=2, padx=15, pady=10, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(log_card, text="Activity & Audit Log", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 5)
        )
        self.log_text = ctk.CTkTextbox(log_card, height=140, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _browse_file(self):
        f = filedialog.askopenfilename(title="Select File to Analyze or Compress")
        if f:
            self._load_path(f, is_folder=False)

    def _browse_folder(self):
        d = filedialog.askdirectory(title="Select Folder to Archive & Compress")
        if d:
            self._load_path(d, is_folder=True)

    def _load_path(self, path_str: str, is_folder: bool):
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, path_str)

        p = Path(path_str)
        if not p.exists():
            messagebox.showerror("Error", f"Path does not exist: {path_str}")
            return

        if is_folder:
            raw_bytes = pack_directory(p)
            self.lbl_info_type.configure(text=f"Type: Directory Archive ({p.name})")
            self.lbl_info_size.configure(text=f"Packed Archive Size: {len(raw_bytes):,} Bytes")
            stats = analyze_bytes(raw_bytes, compute_advanced=False)
            self.lbl_info_entropy.configure(text=f"Shannon Entropy: {stats.shannon_entropy:.4f} bits/symbol")
            self.lbl_info_bound.configure(text=f"Theoretical Min: {stats.theoretical_min_size_bytes:,.1f} Bytes")
            self.set_shared_state("active_data", raw_bytes)
            self.set_shared_state("active_name", p.name)
            self.set_shared_state("is_archive", True)
            self.log(f"Loaded folder archive '{p.name}' ({len(raw_bytes):,} bytes).")
        else:
            with open(p, "rb") as f:
                raw_bytes = f.read()
            self.lbl_info_type.configure(text=f"Type: File ({p.suffix or 'no ext'})")
            self.lbl_info_size.configure(text=f"Size: {len(raw_bytes):,} Bytes")
            stats = analyze_bytes(raw_bytes, compute_advanced=True)
            self.lbl_info_entropy.configure(text=f"Shannon Entropy: {stats.shannon_entropy:.4f} bits/symbol")
            self.lbl_info_bound.configure(text=f"Theoretical Min: {stats.theoretical_min_size_bytes:,.1f} Bytes")
            self.set_shared_state("active_data", raw_bytes)
            self.set_shared_state("active_name", p.name)
            self.set_shared_state("is_archive", False)
            self.set_shared_state("active_stats", stats)
            self.log(f"Loaded file '{p.name}' ({len(raw_bytes):,} bytes, H={stats.shannon_entropy:.4f}).")

    def _get_selected_algorithm_id(self) -> AlgorithmId:
        val = self.algo_dropdown.get()
        mapping = {
            "Huffman": AlgorithmId.HUFFMAN,
            "Arithmetic (Static)": AlgorithmId.ARITHMETIC_STATIC,
            "Arithmetic (Adaptive)": AlgorithmId.ARITHMETIC_ADAPTIVE,
            "Shannon-Fano": AlgorithmId.SHANNON_FANO,
            "LZW": AlgorithmId.LZW,
            "RLE": AlgorithmId.RLE,
            "Delta + Huffman": AlgorithmId.DELTA_HUFFMAN
        }
        return mapping.get(val, AlgorithmId.HUFFMAN)

    def _get_block_size(self) -> int:
        val = self.block_size_opt.get()
        return int(val.split()[0])

    def _do_compress(self):
        data = self.get_shared_state("active_data")
        name = self.get_shared_state("active_name") or "data.bin"
        is_archive = self.get_shared_state("is_archive") or False

        if data is None or len(data) == 0:
            messagebox.showwarning("Warning", "Please select a non-empty file or folder first.")
            return

        algo_id = self._get_selected_algorithm_id()
        block_size = self._get_block_size()
        algo = get_algorithm(algo_id)

        cfg = AlgorithmConfig(algorithm_id=algo_id, block_size=block_size)

        self.log(f"Starting compression with {algo.name} (block_size={block_size})...")
        t0 = time.perf_counter()
        comp_res = algo.compress(data, cfg)
        t_comp = (time.perf_counter() - t0) * 1000.0

        clab_bytes = build_container(comp_res, data, name, is_archive=is_archive)
        total_size = len(clab_bytes)

        # Prompt save
        out_path = filedialog.asksaveasfilename(
            title="Save Compressed File",
            initialfile=f"{name}.clab",
            filetypes=[("Compression Laboratory Container", "*.clab")]
        )
        if out_path:
            with open(out_path, "wb") as f:
                f.write(clab_bytes)

            ratio = len(data) / total_size if total_size > 0 else 0.0
            saving = (len(data) - total_size) / len(data) * 100.0 if len(data) > 0 else 0.0

            self.log(
                f"Successfully compressed to '{Path(out_path).name}' in {t_comp:.2f}ms!\n"
                f"  Original: {len(data):,} B -> Compressed: {total_size:,} B (Payload: {len(comp_res.compressed_bytes):,} B, Model: {len(comp_res.model_metadata):,} B)\n"
                f"  Ratio: {ratio:.3f}x | Space Saving: {saving:.2f}%\n"
                f"  Self-contained file saved to {out_path}."
            )
            messagebox.showinfo("Success", f"Compressed to {Path(out_path).name}\nRatio: {ratio:.2f}x")

    def _do_decompress(self):
        f = filedialog.askopenfilename(
            title="Select .clab File to Decompress",
            filetypes=[("Compression Laboratory Container", "*.clab")]
        )
        if not f:
            return

        try:
            with open(f, "rb") as fl:
                clab_bytes = fl.read()

            t0 = time.perf_counter()
            meta, decomp_bytes = decompress_container(clab_bytes, verify_checksum=True)
            t_decomp = (time.perf_counter() - t0) * 1000.0

            if meta.is_archive:
                out_dir = filedialog.askdirectory(title="Select Extraction Destination Directory")
                if out_dir:
                    extracted = unpack_directory(decomp_bytes, out_dir)
                    self.log(
                        f"Decompressed and verified archive '{Path(f).name}' in {t_decomp:.2f}ms!\n"
                        f"  Extracted {len(extracted)} files/folders to {out_dir}.\n"
                        f"  Integrity: CRC32 0x{meta.original_crc32:08X} MATCH CONFIRMED."
                    )
                    messagebox.showinfo("Success", f"Archive extracted successfully to:\n{out_dir}")
            else:
                suggested_name = meta.filename if meta.filename else "decompressed_file"
                out_file = filedialog.asksaveasfilename(
                    title="Save Decompressed File",
                    initialfile=suggested_name
                )
                if out_file:
                    with open(out_file, "wb") as fl:
                        fl.write(decomp_bytes)
                    self.log(
                        f"Decompressed '{Path(f).name}' -> '{Path(out_file).name}' in {t_decomp:.2f}ms.\n"
                        f"  Reconstructed size: {len(decomp_bytes):,} B.\n"
                        f"  Integrity: CRC32 0x{meta.original_crc32:08X} EXACT MATCH."
                    )
                    messagebox.showinfo("Success", f"File restored and verified:\n{out_file}")

        except Exception as e:
            self.log(f"ERROR: Decompression failed: {e}")
            messagebox.showerror("Decompression Error", str(e))

    def log(self, msg: str):
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see("end")
        if self.log_callback:
            self.log_callback(msg)
