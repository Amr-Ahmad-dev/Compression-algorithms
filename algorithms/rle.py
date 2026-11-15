"""
Run-Length Encoding (RLE) Implementation from scratch.
Uses a PackBits-style binary-safe run-length encoding.
Guarantees exact lossless roundtrip on any arbitrary binary data, text, or repeated patterns.
"""

from typing import List, Optional
from algorithms.base import (
    CompressionAlgorithm,
    AlgorithmId,
    AlgorithmConfig,
    CompressionResult,
    DecompressionResult,
    StepTrace
)


def packbits_compress(data: bytes) -> bytes:
    """
    Compresses data using PackBits RLE.
    Control byte n:
      0 <= n <= 127: (n + 1) literal bytes follow.
      129 <= n <= 255: repeat next 1 byte (257 - n) times (from 2 to 128 repetitions).
      128: no-op.
    """
    if not data:
        return b""

    out = bytearray()
    i = 0
    n = len(data)

    while i < n:
        # Check for run of identical bytes
        run_len = 1
        while i + run_len < n and data[i + run_len] == data[i] and run_len < 128:
            run_len += 1

        if run_len >= 3 or (run_len >= 2 and i + run_len == n):
            # Encode repeated run
            control = (257 - run_len) & 0xFF
            out.append(control)
            out.append(data[i])
            i += run_len
        else:
            # Literal run: find how many literals until next run of >= 3
            lit_start = i
            lit_len = 0
            while i < n and lit_len < 128:
                # Look ahead for a run of 3 identical bytes
                if i + 2 < n and data[i] == data[i + 1] == data[i + 2]:
                    break
                lit_len += 1
                i += 1
            if lit_len > 0:
                out.append(lit_len - 1)
                out.extend(data[lit_start:lit_start + lit_len])

    return bytes(out)


def packbits_decompress(data: bytes, original_size: int) -> bytes:
    """Decompresses PackBits RLE stream."""
    if not data or original_size == 0:
        return b""

    out = bytearray()
    i = 0
    n = len(data)

    while i < n and len(out) < original_size:
        control = data[i]
        i += 1

        if control <= 127:
            # Literal run of control + 1 bytes
            lit_count = control + 1
            if i + lit_count > n:
                raise ValueError("Corrupt RLE stream: literal run exceeds data length.")
            out.extend(data[i:i + lit_count])
            i += lit_count
        elif control > 128:
            # Repeated run
            repeat_count = 257 - control
            if i >= n:
                raise ValueError("Corrupt RLE stream: expected repeated byte.")
            byte_val = data[i]
            i += 1
            out.extend(bytes([byte_val]) * repeat_count)
        # 128 is a no-op / pad byte

    return bytes(out[:original_size])


class RLEAlgorithm(CompressionAlgorithm):
    """Run-Length Encoding algorithm."""

    @property
    def algorithm_id(self) -> AlgorithmId:
        return AlgorithmId.RLE

    @property
    def name(self) -> str:
        return "RLE"

    def compress(
        self,
        data: bytes,
        config: Optional[AlgorithmConfig] = None,
        record_trace: bool = False,
        max_traces: int = 100
    ) -> CompressionResult:
        traces: List[StepTrace] = []
        if not data:
            return CompressionResult(
                compressed_bytes=b"",
                model_metadata=b"",
                original_size=0,
                compressed_payload_size=0,
                total_model_size=0,
                block_size=1,
                algorithm_id=self.algorithm_id,
                traces=[]
            )

        payload = packbits_compress(data)

        if record_trace:
            traces.append(StepTrace(
                step_num=1,
                description=f"Compressed {len(data)} raw bytes into {len(payload)} RLE bytes"
            ))

        return CompressionResult(
            compressed_bytes=payload,
            model_metadata=b"",
            original_size=len(data),
            compressed_payload_size=len(payload),
            total_model_size=0,
            block_size=1,
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
        decompressed = packbits_decompress(compressed_bytes, original_size)
        return DecompressionResult(decompressed_bytes=decompressed, original_size=original_size)
