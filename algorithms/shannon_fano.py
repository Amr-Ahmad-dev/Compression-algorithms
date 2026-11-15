"""
Shannon-Fano Encoding and Decoding Implementation from scratch.
Features:
- Deterministic recursive binary partitioning minimizing frequency divergence.
- Deterministic secondary tie-breaking on symbol bytes.
- Prefix-free codebook construction and serialization.
- Configurable block sizes (1, 2, 3, 4 bytes).
- Step-by-step partition trace for educational visualization.
"""

import struct
from collections import Counter
from typing import Dict, List, Optional, Tuple, Any
from core.bitstream import BitWriter, BitReader
from algorithms.base import (
    CompressionAlgorithm,
    AlgorithmId,
    AlgorithmConfig,
    CompressionResult,
    DecompressionResult,
    StepTrace
)


class ShannonFanoTrieNode:
    """Trie node for decoding prefix-free codewords."""
    __slots__ = ('symbol', 'left', 'right')

    def __init__(self, symbol: Optional[bytes] = None):
        self.symbol = symbol
        self.left: Optional['ShannonFanoTrieNode'] = None
        self.right: Optional['ShannonFanoTrieNode'] = None

    @property
    def is_leaf(self) -> bool:
        return self.symbol is not None


def partition_symbols(
    items: List[Tuple[bytes, int]],
    trace_partitions: Optional[List[Dict[str, Any]]] = None
) -> Dict[bytes, str]:
    """
    Recursively partitions frequency-sorted symbols into two subsets with minimal
    absolute difference in total frequency.
    Returns mapping of symbol -> codeword string ('0' and '1').
    """
    codewords: Dict[bytes, str] = {sym: "" for sym, _ in items}

    if not items:
        return codewords

    if len(items) == 1:
        codewords[items[0][0]] = "0"
        return codewords

    def recurse(sub_items: List[Tuple[bytes, int]], prefix: str, depth: int) -> None:
        if not sub_items:
            return
        if len(sub_items) == 1:
            sym = sub_items[0][0]
            codewords[sym] = prefix if prefix else "0"
            return

        total_weight = sum(w for _, w in sub_items)
        best_diff = float('inf')
        best_split = 1
        running = 0

        # Find split index i where partition 0..i and i..end has minimal difference
        for i in range(len(sub_items) - 1):
            running += sub_items[i][1]
            rem = total_weight - running
            diff = abs(running - rem)
            if diff < best_diff:
                best_diff = diff
                best_split = i + 1

        left_part = sub_items[:best_split]
        right_part = sub_items[best_split:]

        if trace_partitions is not None:
            trace_partitions.append({
                "depth": depth,
                "prefix": prefix,
                "left_symbols": [s[0] for s in left_part],
                "left_weight": sum(s[1] for s in left_part),
                "right_symbols": [s[0] for s in right_part],
                "right_weight": sum(s[1] for s in right_part),
            })

        recurse(left_part, prefix + "0", depth + 1)
        recurse(right_part, prefix + "1", depth + 1)

    recurse(items, "", 0)
    return codewords


def serialize_codebook(codewords: Dict[bytes, str], block_size: int, total_symbols: int) -> bytes:
    """
    Serializes Shannon-Fano codebook:
    - block_size (1B), total_symbols (4B), num_entries (4B)
    - for each entry: sym_len (1B) + sym_bytes + code_len (1B) + packed code bits
    """
    writer = BitWriter()
    # Write header bytes
    header = struct.pack(">BII", block_size, total_symbols, len(codewords))
    writer.write_bytes(header)

    for sym, code in sorted(codewords.items(), key=lambda x: (len(x[1]), x[0])):
        writer.write_bits(len(sym), 8)
        writer.write_bytes(sym)
        writer.write_bits(len(code), 8)
        writer.write_bitstring(code)

    serialized, _ = writer.flush()
    return serialized


def deserialize_codebook(metadata: bytes) -> Tuple[int, int, ShannonFanoTrieNode]:
    """Reconstructs decoding trie from serialized codebook."""
    if len(metadata) < 9:
        raise ValueError("Corrupt Shannon-Fano metadata: header too short.")

    block_size, total_symbols, num_entries = struct.unpack(">BII", metadata[:9])
    reader = BitReader(metadata[9:])
    root = ShannonFanoTrieNode()

    # Edge case: single entry
    if num_entries == 1:
        sym_len = reader.read_bits(8)
        sym = reader.read_bytes(sym_len)
        code_len = reader.read_bits(8)
        _ = reader.read_bitstring(code_len)
        root.symbol = sym
        return block_size, total_symbols, root

    for _ in range(num_entries):
        sym_len = reader.read_bits(8)
        sym = reader.read_bytes(sym_len)
        code_len = reader.read_bits(8)
        code = reader.read_bitstring(code_len)

        # Insert codeword into trie
        curr = root
        for bit_char in code:
            if bit_char == '0':
                if curr.left is None:
                    curr.left = ShannonFanoTrieNode()
                curr = curr.left
            else:
                if curr.right is None:
                    curr.right = ShannonFanoTrieNode()
                curr = curr.right
        curr.symbol = sym

    return block_size, total_symbols, root


class ShannonFanoAlgorithm(CompressionAlgorithm):
    """
    Shannon-Fano Compression Algorithm with deterministic recursive partitioning.
    """

    @property
    def algorithm_id(self) -> AlgorithmId:
        return AlgorithmId.SHANNON_FANO

    @property
    def name(self) -> str:
        return "Shannon-Fano"

    def compress(
        self,
        data: bytes,
        config: Optional[AlgorithmConfig] = None,
        record_trace: bool = False,
        max_traces: int = 100
    ) -> CompressionResult:
        block_size = config.block_size if config else 1
        if block_size < 1:
            block_size = 1

        traces: List[StepTrace] = []

        if not data:
            return CompressionResult(
                compressed_bytes=b"",
                model_metadata=b"",
                original_size=0,
                compressed_payload_size=0,
                total_model_size=0,
                block_size=block_size,
                algorithm_id=self.algorithm_id,
                traces=[]
            )

        blocks = [data[i:i + block_size] for i in range(0, len(data), block_size)]
        total_symbols = len(blocks)

        # Frequency calculation
        freq = Counter(blocks)
        # Sort descending by frequency; tie-breaker: ascending by symbol bytes
        sorted_items = sorted(freq.items(), key=lambda x: (-x[1], x[0]))

        partition_logs: List[Dict[str, Any]] = []
        codewords = partition_symbols(sorted_items, partition_logs if record_trace else None)

        model_metadata = serialize_codebook(codewords, block_size, total_symbols)

        writer = BitWriter()
        for idx, block in enumerate(blocks):
            code = codewords[block]
            writer.write_bitstring(code)

            if record_trace and len(traces) < max_traces:
                traces.append(StepTrace(
                    step_num=idx + 1,
                    description=f"Symbol {block!r} -> Code {code}",
                    symbol=block,
                    codeword=code,
                    state={"remaining": total_symbols - idx - 1}
                ))

        compressed_payload, _ = writer.flush()

        return CompressionResult(
            compressed_bytes=compressed_payload,
            model_metadata=model_metadata,
            original_size=len(data),
            compressed_payload_size=len(compressed_payload),
            total_model_size=len(model_metadata),
            block_size=block_size,
            algorithm_id=self.algorithm_id,
            traces=traces
        )

    def decompress(
        self,
        compressed_bytes: bytes,
        model_metadata: bytes,
        original_size: int,
        config: Optional[AlgorithmConfig] = None,
        record_trace: bool = False,
        max_traces: int = 100
    ) -> DecompressionResult:
        if original_size == 0:
            return DecompressionResult(decompressed_bytes=b"", original_size=0)

        block_size, total_symbols, root = deserialize_codebook(model_metadata)

        # Single unique symbol edge case
        if root.is_leaf:
            single_sym = root.symbol or b""
            return DecompressionResult(
                decompressed_bytes=(single_sym * total_symbols)[:original_size],
                original_size=original_size
            )

        reader = BitReader(compressed_bytes)
        output_blocks: List[bytes] = []
        traces: List[StepTrace] = []

        curr = root
        symbols_decoded = 0

        while symbols_decoded < total_symbols and reader.has_more():
            bit = reader.read_bit()
            curr = curr.right if bit else curr.left

            if curr is None:
                raise ValueError("Corrupt Shannon-Fano stream: branch traversal failed.")

            if curr.is_leaf:
                sym = curr.symbol or b""
                output_blocks.append(sym)
                symbols_decoded += 1

                if record_trace and len(traces) < max_traces:
                    traces.append(StepTrace(
                        step_num=symbols_decoded,
                        description=f"Decoded {sym!r}",
                        symbol=sym,
                        state={"count": symbols_decoded, "total": total_symbols}
                    ))

                curr = root

        reconstructed = b"".join(output_blocks)
        if len(reconstructed) != original_size:
            reconstructed = reconstructed[:original_size]

        return DecompressionResult(
            decompressed_bytes=reconstructed,
            original_size=original_size,
            traces=traces
        )
