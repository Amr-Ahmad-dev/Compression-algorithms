"""
Lempel-Ziv-Welch (LZW) Compression Algorithm from scratch.
Features:
- Pure dictionary-based lossless compression.
- Solves classic KwKwK edge case on decompression.
- Configurable maximum dictionary size and bit width.
- 16-bit code output with metadata container.
- Step-by-step trace generation for dictionary evolution.
"""

import struct
from typing import Dict, List, Optional
from algorithms.base import (
    CompressionAlgorithm,
    AlgorithmId,
    AlgorithmConfig,
    CompressionResult,
    DecompressionResult,
    StepTrace
)


class LZWAlgorithm(CompressionAlgorithm):
    """
    Lempel-Ziv-Welch (LZW) compression implementation.
    """

    @property
    def algorithm_id(self) -> AlgorithmId:
        return AlgorithmId.LZW

    @property
    def name(self) -> str:
        return "LZW"

    def compress(
        self,
        data: bytes,
        config: Optional[AlgorithmConfig] = None,
        record_trace: bool = False,
        max_traces: int = 100
    ) -> CompressionResult:
        max_dict_size = config.max_dict_size if config else 65535
        if max_dict_size > 65535:
            max_dict_size = 65535
        if max_dict_size < 257:
            max_dict_size = 257

        traces: List[StepTrace] = []

        if not data:
            return CompressionResult(
                compressed_bytes=b"",
                model_metadata=struct.pack(">H", max_dict_size),
                original_size=0,
                compressed_payload_size=0,
                total_model_size=2,
                block_size=1,
                algorithm_id=self.algorithm_id,
                traces=[]
            )

        dictionary: Dict[bytes, int] = {bytes([i]): i for i in range(256)}
        next_code = 256
        w = b""
        codes: List[int] = []

        for idx, byte_val in enumerate(data):
            c = bytes([byte_val])
            wc = w + c
            if wc in dictionary:
                w = wc
            else:
                code_to_emit = dictionary[w]
                codes.append(code_to_emit)

                if record_trace and len(traces) < max_traces:
                    traces.append(StepTrace(
                        step_num=len(codes),
                        description=f"Output code {code_to_emit} for string {w!r}, added {wc!r} as {next_code}",
                        symbol=w,
                        codeword=str(code_to_emit),
                        state={"dict_size": len(dictionary)}
                    ))

                if next_code < max_dict_size:
                    dictionary[wc] = next_code
                    next_code += 1
                w = c

        if w:
            codes.append(dictionary[w])

        # Pack codes as 16-bit big-endian unsigned integers
        payload = bytearray()
        for code in codes:
            payload.extend(struct.pack(">H", code))

        model_metadata = struct.pack(">H", max_dict_size)

        return CompressionResult(
            compressed_bytes=bytes(payload),
            model_metadata=model_metadata,
            original_size=len(data),
            compressed_payload_size=len(payload),
            total_model_size=len(model_metadata),
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
        if original_size == 0:
            return DecompressionResult(decompressed_bytes=b"", original_size=0)

        if len(model_metadata) < 2:
            max_dict_size = 65535
        else:
            max_dict_size = struct.unpack(">H", model_metadata[:2])[0]

        # Unpack 16-bit codes
        num_codes = len(compressed_bytes) // 2
        if num_codes == 0:
            return DecompressionResult(decompressed_bytes=b"", original_size=0)

        codes = [struct.unpack(">H", compressed_bytes[i * 2:(i + 1) * 2])[0] for i in range(num_codes)]

        dictionary: Dict[int, bytes] = {i: bytes([i]) for i in range(256)}
        next_code = 256

        w = dictionary[codes[0]]
        out = bytearray(w)
        traces: List[StepTrace] = []

        for step, code in enumerate(codes[1:], start=2):
            if code in dictionary:
                entry = dictionary[code]
            elif code == next_code:
                # Classic LZW edge case: cScSc
                entry = w + bytes([w[0]])
            else:
                raise ValueError(f"Corrupt LZW code {code} at step {step} (dict size: {len(dictionary)})")

            out.extend(entry)

            if record_trace and len(traces) < max_traces:
                traces.append(StepTrace(
                    step_num=step,
                    description=f"Decoded code {code} -> {entry!r}",
                    symbol=entry,
                    codeword=str(code),
                    state={"dict_size": len(dictionary)}
                ))

            if next_code < max_dict_size:
                dictionary[next_code] = w + bytes([entry[0]])
                next_code += 1

            w = entry

        return DecompressionResult(
            decompressed_bytes=bytes(out[:original_size]),
            original_size=original_size,
            traces=traces
        )
