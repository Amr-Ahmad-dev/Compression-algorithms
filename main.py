"""
Main Entry Point for the File Compression Laboratory.
Supports both Graphical Desktop UI and Headless CLI / Benchmarking modes.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from algorithms import ALGORITHM_REGISTRY, get_algorithm
from algorithms.base import AlgorithmId, AlgorithmConfig
from core.container import build_container, decompress_container
from core.statistics import analyze_bytes
from analysis.benchmark import TournamentRunner, TournamentEntry


def run_cli_demo():
    print("=" * 70)
    print("🔬 ANTIGRAVITY FILE COMPRESSION LABORATORY — CLI BENCHMARK")
    print("=" * 70)

    sample_text = (
        "Information theory establishes fundamental limits on data compression and communication. "
        "Claude Shannon proved that the shortest average code length for lossless compression "
        "is bounded below by the Shannon entropy H(X) = -sum p(x) log2 p(x). "
        "Algorithms tested: Huffman, Arithmetic (Static & Adaptive), Shannon-Fano, LZW, RLE! "
    ) * 15
    data = sample_text.encode("utf-8")

    print(f"\n[+] Input Data Size: {len(data):,} bytes")
    stats = analyze_bytes(data, compute_advanced=True)
    print(f"[+] Shannon Entropy: {stats.shannon_entropy:.4f} bits/symbol (Max: {stats.max_entropy:.2f})")
    print(f"[+] Theoretical Shannon Bound: {stats.theoretical_min_size_bytes:,.1f} bytes")
    print(f"[+] Conditional Entropy H(X|Y): {stats.conditional_entropy:.4f} bits/symbol")

    competitors = [
        TournamentEntry(AlgorithmId.HUFFMAN, "Huffman (Byte)", AlgorithmConfig(AlgorithmId.HUFFMAN, block_size=1)),
        TournamentEntry(AlgorithmId.HUFFMAN, "Huffman (BS=2)", AlgorithmConfig(AlgorithmId.HUFFMAN, block_size=2)),
        TournamentEntry(AlgorithmId.ARITHMETIC_STATIC, "Arithmetic (Static)", AlgorithmConfig(AlgorithmId.ARITHMETIC_STATIC, block_size=1)),
        TournamentEntry(AlgorithmId.ARITHMETIC_ADAPTIVE, "Arithmetic (Adaptive)", AlgorithmConfig(AlgorithmId.ARITHMETIC_ADAPTIVE, block_size=1)),
        TournamentEntry(AlgorithmId.SHANNON_FANO, "Shannon-Fano", AlgorithmConfig(AlgorithmId.SHANNON_FANO, block_size=1)),
        TournamentEntry(AlgorithmId.LZW, "LZW (Dictionary)", AlgorithmConfig(AlgorithmId.LZW, block_size=1)),
        TournamentEntry(AlgorithmId.RLE, "RLE (PackBits)", AlgorithmConfig(AlgorithmId.RLE, block_size=1)),
        TournamentEntry(AlgorithmId.DELTA_HUFFMAN, "Delta + Huffman", AlgorithmConfig(AlgorithmId.DELTA_HUFFMAN, block_size=1)),
    ]

    runner = TournamentRunner()
    records = runner.run_single_competition(data, "sample_benchmark.txt", competitors)

    print("\n" + "=" * 96)
    print(f"{'Rank':<4} | {'Algorithm':<22} | {'Container Size':<14} | {'Ratio':<7} | {'Saving':<7} | {'Comp(ms)':<8} | {'Decomp(ms)':<10} | {'Integrity'}")
    print("-" * 96)
    for r in sorted(records, key=lambda x: x.rank_size):
        integ = "✓ PASS" if r.integrity_verified else "✗ FAIL"
        print(
            f"#{r.rank_size:<3} | {r.algorithm_name:<22} | {r.compressed_container_size:<14} | "
            f"{r.compression_ratio:<7.2f} | {r.space_saving_percent:<6.1f}% | "
            f"{r.compression_time_ms:<8.2f} | {r.decompression_time_ms:<10.2f} | {integ}"
        )
    print("=" * 96)

    best = min(records, key=lambda r: r.compressed_container_size)
    print(f"\n🏆 Tournament Winner: {best.algorithm_name} ({best.compressed_container_size} bytes, {best.compression_ratio:.2f}x compression)")


def main():
    parser = argparse.ArgumentParser(description="File Compression Laboratory")
    parser.add_argument("--cli", action="store_true", help="Run command-line benchmark tournament demo")
    parser.add_argument("--file", type=str, help="Compress or inspect a specific file from CLI")
    args = parser.parse_args()

    if args.cli:
        run_cli_demo()
    elif args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"Error: file not found: {args.file}")
            sys.exit(1)
        with open(p, "rb") as f:
            data = f.read()
        print(f"Analyzing {p.name} ({len(data):,} bytes)...")
        stats = analyze_bytes(data, compute_advanced=True)
        print(f"Shannon Entropy: {stats.shannon_entropy:.4f} bits")
        print(f"Theoretical Lower Bound: {stats.theoretical_min_size_bytes:,.1f} bytes")
    else:
        try:
            from interface.app import run_app
            run_app()
        except Exception as e:
            print(f"Note: Could not initialize GUI ({e}). Falling back to CLI demo.")
            run_cli_demo()


if __name__ == "__main__":
    main()
