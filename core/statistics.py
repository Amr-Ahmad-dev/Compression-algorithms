"""
Statistical Analysis and Information Theory Engine.
Calculates Shannon entropy, probability distributions, autocorrelation,
conditional entropy, n-grams, and theoretical compression limits.
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, BinaryIO


@dataclass
class FileStatistics:
    total_bytes: int
    unique_symbols: int
    shannon_entropy: float
    max_entropy: float
    entropy_per_symbol: float
    theoretical_min_size_bytes: float
    zero_byte_count: int
    zero_byte_ratio: float
    printable_count: int
    printable_ratio: float
    ascii_count: int
    ascii_ratio: float
    byte_frequencies: Dict[int, int]
    byte_probabilities: Dict[int, float]
    top_symbols: List[Tuple[int, int, float]]  # (byte, count, prob)
    bottom_symbols: List[Tuple[int, int, float]]
    conditional_entropy: float = 0.0
    autocorrelation: List[float] = field(default_factory=list)
    top_bigrams: List[Tuple[Tuple[int, int], int, float]] = field(default_factory=list)
    chunk_entropies: List[float] = field(default_factory=list)


def calculate_entropy(frequencies: Dict[int, int], total_count: int) -> float:
    """Calculate Shannon entropy H(X) = -sum(p * log2(p))."""
    if total_count <= 0:
        return 0.0
    entropy = 0.0
    for count in frequencies.values():
        if count > 0:
            p = count / total_count
            entropy -= p * math.log2(p)
    return entropy


def calculate_entropy_from_data(data: bytes) -> float:
    """Convenience helper to compute Shannon entropy for raw bytes."""
    if not data:
        return 0.0
    freq = Counter(data)
    return calculate_entropy(freq, len(data))


def calculate_theoretical_bound(data_size: int, entropy: float) -> float:
    """Theoretical lower bound in bytes for lossless compression under 0-th order model."""
    return (data_size * entropy) / 8.0


def calculate_coding_metrics(data_size: int, compressed_size: int, entropy: float) -> Dict[str, float]:
    """
    Computes compression ratio, space saving, coding efficiency, and redundancy.
    """
    ratio = (data_size / compressed_size) if compressed_size > 0 else 0.0
    saving_pct = ((data_size - compressed_size) / data_size * 100.0) if data_size > 0 else 0.0
    avg_bits_per_symbol = (compressed_size * 8.0 / data_size) if data_size > 0 else 0.0
    efficiency = (entropy / avg_bits_per_symbol) if avg_bits_per_symbol > 0 else 0.0
    redundancy = (1.0 - efficiency) if efficiency <= 1.0 else 0.0

    return {
        "compression_ratio": ratio,
        "space_saving_percent": saving_pct,
        "avg_code_length_bits": avg_bits_per_symbol,
        "coding_efficiency": efficiency,
        "redundancy": redundancy,
    }


def analyze_bytes(data: bytes, compute_advanced: bool = True) -> FileStatistics:
    """
    Comprehensive in-memory statistical and information-theoretic analysis of byte data.
    """
    total_bytes = len(data)
    if total_bytes == 0:
        return FileStatistics(
            total_bytes=0,
            unique_symbols=0,
            shannon_entropy=0.0,
            max_entropy=8.0,
            entropy_per_symbol=0.0,
            theoretical_min_size_bytes=0.0,
            zero_byte_count=0,
            zero_byte_ratio=0.0,
            printable_count=0,
            printable_ratio=0.0,
            ascii_count=0,
            ascii_ratio=0.0,
            byte_frequencies={i: 0 for i in range(256)},
            byte_probabilities={i: 0.0 for i in range(256)},
            top_symbols=[],
            bottom_symbols=[],
            conditional_entropy=0.0,
            autocorrelation=[0.0] * 32,
            top_bigrams=[],
            chunk_entropies=[]
        )

    # 1. Frequency counts
    freq = Counter(data)
    byte_frequencies = {i: freq.get(i, 0) for i in range(256)}
    byte_probabilities = {i: byte_frequencies[i] / total_bytes for i in range(256)}
    unique_symbols = sum(1 for c in byte_frequencies.values() if c > 0)

    # 2. Shannon Entropy
    entropy = calculate_entropy(byte_frequencies, total_bytes)
    max_entropy = math.log2(256) if unique_symbols > 0 else 0.0
    theoretical_min = calculate_theoretical_bound(total_bytes, entropy)

    # 3. Categorical distribution
    zero_bytes = byte_frequencies[0]
    # Printable ASCII: 32..126 plus newline, tab, carriage return (9, 10, 13)
    printable_set = set(range(32, 127)) | {9, 10, 13}
    printable_count = sum(byte_frequencies[b] for b in printable_set)
    ascii_count = sum(byte_frequencies[b] for b in range(128))

    # 4. Top and bottom symbols
    sorted_symbols = sorted(
        [(b, count, count / total_bytes) for b, count in byte_frequencies.items() if count > 0],
        key=lambda x: x[1],
        reverse=True
    )
    top_symbols = sorted_symbols[:10]
    bottom_symbols = sorted_symbols[-10:] if len(sorted_symbols) > 10 else list(reversed(sorted_symbols))

    # 5. Advanced statistics (Conditional entropy, Autocorrelation, Bigrams, Local chunk entropy)
    cond_entropy = 0.0
    autocorr = [0.0] * 32
    top_bigrams: List[Tuple[Tuple[int, int], int, float]] = []
    chunk_entropies: List[float] = []

    if compute_advanced and total_bytes > 1:
        # Bigram frequencies and conditional entropy H(X_i | X_{i-1})
        bigram_counts = Counter()
        for i in range(total_bytes - 1):
            bigram_counts[(data[i], data[i + 1])] += 1

        total_bigrams = total_bytes - 1
        # H(X_i, X_{i-1}) joint entropy
        joint_entropy = 0.0
        for count in bigram_counts.values():
            p_xy = count / total_bigrams
            joint_entropy -= p_xy * math.log2(p_xy)

        # H(X_i | X_{i-1}) = H(X, Y) - H(X)
        cond_entropy = max(0.0, joint_entropy - entropy)

        sorted_bigrams = sorted(bigram_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_bigrams = [(bg, cnt, cnt / total_bigrams) for bg, cnt in sorted_bigrams]

        # Byte Autocorrelation for lags 1..32
        mean_val = sum(data) / total_bytes
        variance = sum((x - mean_val) ** 2 for x in data) / total_bytes

        if variance > 1e-9:
            max_lag = min(32, total_bytes - 1)
            for k in range(1, max_lag + 1):
                cov = sum((data[i] - mean_val) * (data[i + k] - mean_val) for i in range(total_bytes - k)) / (total_bytes - k)
                autocorr[k - 1] = cov / variance

        # Local chunk entropy profile across file (e.g. 50 chunks)
        num_chunks = min(50, total_bytes // 32) if total_bytes >= 32 else 1
        if num_chunks > 1:
            chunk_size = total_bytes // num_chunks
            for i in range(num_chunks):
                start = i * chunk_size
                end = (i + 1) * chunk_size if i < num_chunks - 1 else total_bytes
                chunk_slice = data[start:end]
                chunk_entropies.append(calculate_entropy_from_data(chunk_slice))
        else:
            chunk_entropies.append(entropy)

    return FileStatistics(
        total_bytes=total_bytes,
        unique_symbols=unique_symbols,
        shannon_entropy=entropy,
        max_entropy=max_entropy,
        entropy_per_symbol=entropy,
        theoretical_min_size_bytes=theoretical_min,
        zero_byte_count=zero_bytes,
        zero_byte_ratio=zero_bytes / total_bytes,
        printable_count=printable_count,
        printable_ratio=printable_count / total_bytes,
        ascii_count=ascii_count,
        ascii_ratio=ascii_count / total_bytes,
        byte_frequencies=byte_frequencies,
        byte_probabilities=byte_probabilities,
        top_symbols=top_symbols,
        bottom_symbols=bottom_symbols,
        conditional_entropy=cond_entropy,
        autocorrelation=autocorr,
        top_bigrams=top_bigrams,
        chunk_entropies=chunk_entropies
    )


def analyze_file_streaming(filepath: str, chunk_size: int = 65536) -> FileStatistics:
    """
    Streaming statistical analyzer for large files without loading entire file into memory.
    """
    freq = Counter()
    total_bytes = 0
    zero_bytes = 0
    printable_count = 0
    ascii_count = 0
    printable_set = set(range(32, 127)) | {9, 10, 13}

    # First pass: count frequencies
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            for b in chunk:
                freq[b] += 1
                if b == 0:
                    zero_bytes += 1
                if b in printable_set:
                    printable_count += 1
                if b < 128:
                    ascii_count += 1

    byte_frequencies = {i: freq.get(i, 0) for i in range(256)}
    if total_bytes == 0:
        return analyze_bytes(b"")

    byte_probabilities = {i: byte_frequencies[i] / total_bytes for i in range(256)}
    unique_symbols = sum(1 for c in byte_frequencies.values() if c > 0)
    entropy = calculate_entropy(byte_frequencies, total_bytes)
    theoretical_min = calculate_theoretical_bound(total_bytes, entropy)

    sorted_symbols = sorted(
        [(b, count, count / total_bytes) for b, count in byte_frequencies.items() if count > 0],
        key=lambda x: x[1],
        reverse=True
    )
    top_symbols = sorted_symbols[:10]
    bottom_symbols = sorted_symbols[-10:] if len(sorted_symbols) > 10 else list(reversed(sorted_symbols))

    return FileStatistics(
        total_bytes=total_bytes,
        unique_symbols=unique_symbols,
        shannon_entropy=entropy,
        max_entropy=8.0,
        entropy_per_symbol=entropy,
        theoretical_min_size_bytes=theoretical_min,
        zero_byte_count=zero_bytes,
        zero_byte_ratio=zero_bytes / total_bytes,
        printable_count=printable_count,
        printable_ratio=printable_count / total_bytes,
        ascii_count=ascii_count,
        ascii_ratio=ascii_count / total_bytes,
        byte_frequencies=byte_frequencies,
        byte_probabilities=byte_probabilities,
        top_symbols=top_symbols,
        bottom_symbols=bottom_symbols
    )
