"""
Benchmarking and Tournament System for the Compression Laboratory.
Executes fair side-by-side compression competitions with exact binary container measurements,
integrity verification, ranking metrics, and CSV/JSON export.
"""

import time
import json
import csv
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from algorithms.base import AlgorithmId, AlgorithmConfig, CompressionAlgorithm
from algorithms import get_algorithm
from core.container import build_container, decompress_container
from core.statistics import analyze_bytes


@dataclass
class TournamentEntry:
    algorithm_id: AlgorithmId
    name: str
    config: AlgorithmConfig


@dataclass
class BenchmarkRecord:
    dataset_name: str
    algorithm_name: str
    algorithm_id: int
    block_size: int
    original_size: int
    compressed_container_size: int
    payload_size: int
    model_metadata_size: int
    compression_ratio: float
    space_saving_percent: float
    compression_time_ms: float
    decompression_time_ms: float
    source_entropy: float
    theoretical_min_bytes: float
    integrity_verified: bool
    rank_size: int = 0
    rank_speed: int = 0


class TournamentRunner:
    """Executes compression tournaments across algorithms and datasets."""

    def __init__(self):
        self.records: List[BenchmarkRecord] = []

    def run_single_competition(
        self,
        data: bytes,
        dataset_name: str,
        competitors: List[TournamentEntry]
    ) -> List[BenchmarkRecord]:
        """
        Runs all competitors against the same raw byte input.
        Verifies reconstruction for every entry.
        """
        stats = analyze_bytes(data, compute_advanced=False)
        entropy = stats.shannon_entropy
        orig_size = len(data)
        theo_min = stats.theoretical_min_size_bytes

        batch_records: List[BenchmarkRecord] = []

        for comp in competitors:
            algo = get_algorithm(comp.algorithm_id)

            # 1. Measure Compression Time
            t0 = time.perf_counter()
            comp_res = algo.compress(data, comp.config)
            t_comp = (time.perf_counter() - t0) * 1000.0

            # 2. Package into full self-contained container
            clab_bytes = build_container(comp_res, data, dataset_name, is_archive=False)
            total_size = len(clab_bytes)

            # 3. Measure Decompression Time & Verify Integrity
            t0 = time.perf_counter()
            meta, decomp_data = decompress_container(clab_bytes, verify_checksum=True)
            t_decomp = (time.perf_counter() - t0) * 1000.0

            verified = (decomp_data == data)
            if not verified:
                raise RuntimeError(
                    f"FATAL: Algorithm {comp.name} failed roundtrip integrity verification on dataset {dataset_name}!"
                )

            ratio = (orig_size / total_size) if total_size > 0 else 0.0
            saving = ((orig_size - total_size) / orig_size * 100.0) if orig_size > 0 else 0.0

            record = BenchmarkRecord(
                dataset_name=dataset_name,
                algorithm_name=comp.name,
                algorithm_id=int(comp.algorithm_id),
                block_size=comp.config.block_size,
                original_size=orig_size,
                compressed_container_size=total_size,
                payload_size=comp_res.compressed_payload_size,
                model_metadata_size=comp_res.total_model_size,
                compression_ratio=ratio,
                space_saving_percent=saving,
                compression_time_ms=round(t_comp, 3),
                decompression_time_ms=round(t_decomp, 3),
                source_entropy=round(entropy, 4),
                theoretical_min_bytes=round(theo_min, 1),
                integrity_verified=verified
            )
            batch_records.append(record)

        # Compute rankings
        # Size ranking (smaller container is better)
        sorted_by_size = sorted(batch_records, key=lambda r: r.compressed_container_size)
        for rank, r in enumerate(sorted_by_size, start=1):
            r.rank_size = rank

        # Speed ranking (fastest total time is better)
        sorted_by_speed = sorted(batch_records, key=lambda r: (r.compression_time_ms + r.decompression_time_ms))
        for rank, r in enumerate(sorted_by_speed, start=1):
            r.rank_speed = rank

        self.records.extend(batch_records)
        return batch_records

    def export_to_csv(self, filepath: str) -> None:
        """Exports all recorded benchmark results to CSV."""
        if not self.records:
            return
        fieldnames = list(asdict(self.records[0]).keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in self.records:
                writer.writerow(asdict(r))

    def export_to_json(self, filepath: str) -> None:
        """Exports all recorded benchmark results to JSON."""
        data = [asdict(r) for r in self.records]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
