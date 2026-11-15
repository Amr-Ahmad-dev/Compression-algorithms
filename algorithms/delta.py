"""
Delta Encoding / Preprocessing transformation.
A reversible byte-difference transformation that transforms smooth or correlated
byte sequences into low-magnitude, low-entropy distributions.
"""

from typing import Optional
from algorithms.base import (
    CompressionAlgorithm,
    AlgorithmId,
    AlgorithmConfig,
    CompressionResult,
    DecompressionResult
)
from algorithms.huffman import HuffmanAlgorithm


def delta_encode(data: bytes) -> bytes:
    """Computes y[0] = x[0], y[i] = (x[i] - x[i-1]) % 256."""
    if not data:
        return b""
    out = bytearray(len(data))
    out[0] = data[0]
    for i in range(1, len(data)):
        out[i] = (data[i] - data[i - 1]) & 0xFF
    return bytes(out)


def delta_decode(data: bytes) -> bytes:
    """Computes x[0] = y[0], x[i] = (x[i-1] + y[i]) % 256."""
    if not data:
        return b""
    out = bytearray(len(data))
    out[0] = data[0]
    for i in range(1, len(data)):
        out[i] = (out[i - 1] + data[i]) & 0xFF
    return bytes(out)


class DeltaHuffmanAlgorithm(CompressionAlgorithm):
    """
    Delta-preprocessed Huffman algorithm.
    Applies reversible byte-differencing followed by Huffman compression.
    """
    def __init__(self):
        self._huffman = HuffmanAlgorithm()

    @property
    def algorithm_id(self) -> AlgorithmId:
        return AlgorithmId.DELTA_HUFFMAN

    @property
    def name(self) -> str:
        return "Delta + Huffman"

    def compress(
        self,
        data: bytes,
        config: Optional[AlgorithmConfig] = None,
        record_trace: bool = False,
        max_traces: int = 100
    ) -> CompressionResult:
        delta_data = delta_encode(data)
        res = self._huffman.compress(delta_data, config, record_trace, max_traces)
        return CompressionResult(
            compressed_bytes=res.compressed_bytes,
            model_metadata=res.model_metadata,
            original_size=len(data),
            compressed_payload_size=res.compressed_payload_size,
            total_model_size=res.total_model_size,
            block_size=res.block_size,
            algorithm_id=self.algorithm_id,
            traces=res.traces
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
        huff_res = self._huffman.decompress(
            compressed_bytes,
            model_metadata,
            original_size,
            config,
            record_trace,
            max_traces
        )
        original = delta_decode(huff_res.decompressed_bytes)
        return DecompressionResult(
            decompressed_bytes=original,
            original_size=original_size,
            traces=huff_res.traces
        )
