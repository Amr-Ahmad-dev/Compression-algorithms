"""
Integer-based Arithmetic Coding Implementation from scratch.
Features:
- Pure integer arithmetic (32-bit precision default, numerically safe).
- Ward / Witten, Neal, and Cleary (WNC) normalization with underflow handling (E3).
- Static probability model (frequencies stored in container metadata).
- Adaptive probability model (dynamic online learning with frequency rescaling).
- Configurable symbol granularity (byte-level, block-level).
- Step-by-step trace generation for interval narrowing visualization.
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


class FrequencyTable:
    """
    Cumulative frequency table for arithmetic coding.
    Maintains:
    - Ordered list of unique symbols.
    - Individual frequencies.
    - Cumulative lower and upper bounds for each symbol.
    - Total frequency sum.
    """
    def __init__(self, symbols: List[bytes], counts: Optional[List[int]] = None):
        self.symbols: List[bytes] = list(symbols)
        self.symbol_to_index: Dict[bytes, int] = {sym: idx for idx, sym in enumerate(self.symbols)}
        if counts is not None:
            self.counts: List[int] = list(counts)
        else:
            self.counts: List[int] = [1] * len(self.symbols)  # Uniform default

        self.cum_freq: List[int] = []
        self.total: int = 0
        self._rebuild_cumulative()

    def _rebuild_cumulative(self) -> None:
        self.cum_freq = [0] * (len(self.counts) + 1)
        running = 0
        for i, c in enumerate(self.counts):
            self.cum_freq[i] = running
            running += c
        self.cum_freq[-1] = running
        self.total = running

    def get_range(self, symbol: bytes) -> Tuple[int, int, int]:
        """Returns (low_count, high_count, total)."""
        idx = self.symbol_to_index[symbol]
        return self.cum_freq[idx], self.cum_freq[idx + 1], self.total

    def get_symbol_at_offset(self, offset: int) -> Tuple[bytes, int, int]:
        """
        Binary search or linear scan to find symbol whose interval covers offset.
        Returns (symbol, low_count, high_count).
        """
        # Binary search in cumulative frequencies
        low = 0
        high = len(self.symbols) - 1
        while low <= high:
            mid = (low + high) // 2
            if self.cum_freq[mid + 1] <= offset:
                low = mid + 1
            elif self.cum_freq[mid] > offset:
                high = mid - 1
            else:
                return self.symbols[mid], self.cum_freq[mid], self.cum_freq[mid + 1]
        raise ValueError(f"Offset {offset} outside valid cumulative range 0..{self.total}")

    def increment(self, symbol: bytes, rescale_threshold: int = 16384) -> None:
        """Increment symbol frequency for adaptive modeling, with rescaling."""
        idx = self.symbol_to_index[symbol]
        self.counts[idx] += 1
        self.total += 1

        # Periodic rescaling when total reaches threshold to prevent integer growth
        if self.total >= rescale_threshold:
            for i in range(len(self.counts)):
                self.counts[i] = max(1, self.counts[i] // 2)
            self._rebuild_cumulative()
        else:
            # Incremental update for subsequent cumulative positions
            for i in range(idx + 1, len(self.cum_freq)):
                self.cum_freq[i] += 1


class ArithmeticEncoder:
    """Integer arithmetic encoder with 32-bit bounds and E3 underflow handling."""

    def __init__(self, precision: int = 32):
        self.precision = precision
        self.max_int = (1 << precision) - 1
        self.half = 1 << (precision - 1)
        self.first_qtr = self.half >> 1
        self.third_qtr = self.first_qtr * 3

        self.low = 0
        self.high = self.max_int
        self.pending_bits = 0
        self.writer = BitWriter()

    def encode_symbol(self, low_count: int, high_count: int, total: int) -> None:
        rng = self.high - self.low + 1
        self.high = self.low + (rng * high_count) // total - 1
        self.low = self.low + (rng * low_count) // total

        # Renormalization loop
        while True:
            if self.high < self.half:
                # E1: high < half -> MSB is 0
                self.writer.write_bit(0)
                for _ in range(self.pending_bits):
                    self.writer.write_bit(1)
                self.pending_bits = 0
                self.low = (self.low << 1) & self.max_int
                self.high = ((self.high << 1) | 1) & self.max_int
            elif self.low >= self.half:
                # E2: low >= half -> MSB is 1
                self.writer.write_bit(1)
                for _ in range(self.pending_bits):
                    self.writer.write_bit(0)
                self.pending_bits = 0
                self.low = ((self.low - self.half) << 1) & self.max_int
                self.high = (((self.high - self.half) << 1) | 1) & self.max_int
            elif self.low >= self.first_qtr and self.high < self.third_qtr:
                # E3: Underflow condition: straddling half
                self.pending_bits += 1
                self.low = ((self.low - self.first_qtr) << 1) & self.max_int
                self.high = (((self.high - self.first_qtr) << 1) | 1) & self.max_int
            else:
                break

    def finish(self) -> Tuple[bytes, int]:
        """Flushes final interval-identifying bits."""
        self.pending_bits += 1
        if self.low < self.first_qtr:
            self.writer.write_bit(0)
            for _ in range(self.pending_bits):
                self.writer.write_bit(1)
        else:
            self.writer.write_bit(1)
            for _ in range(self.pending_bits):
                self.writer.write_bit(0)
        return self.writer.flush()


class ArithmeticDecoder:
    """Integer arithmetic decoder matching the encoder bounds."""

    def __init__(self, reader: BitReader, precision: int = 32):
        self.precision = precision
        self.max_int = (1 << precision) - 1
        self.half = 1 << (precision - 1)
        self.first_qtr = self.half >> 1
        self.third_qtr = self.first_qtr * 3

        self.reader = reader
        self.low = 0
        self.high = self.max_int
        self.value = 0

        # Prime the decoder with first `precision` bits
        for _ in range(precision):
            bit = self.reader.read_bit() if self.reader.has_more() else 0
            self.value = (self.value << 1) | bit

    def get_current_offset(self, total: int) -> int:
        rng = self.high - self.low + 1
        offset = ((self.value - self.low + 1) * total - 1) // rng
        return offset

    def update_range(self, low_count: int, high_count: int, total: int) -> None:
        rng = self.high - self.low + 1
        self.high = self.low + (rng * high_count) // total - 1
        self.low = self.low + (rng * low_count) // total

        while True:
            if self.high < self.half:
                self.low = (self.low << 1) & self.max_int
                self.high = ((self.high << 1) | 1) & self.max_int
                bit = self.reader.read_bit() if self.reader.has_more() else 0
                self.value = ((self.value << 1) | bit) & self.max_int
            elif self.low >= self.half:
                self.low = ((self.low - self.half) << 1) & self.max_int
                self.high = (((self.high - self.half) << 1) | 1) & self.max_int
                bit = self.reader.read_bit() if self.reader.has_more() else 0
                self.value = (((self.value - self.half) << 1) | bit) & self.max_int
            elif self.low >= self.first_qtr and self.high < self.third_qtr:
                self.low = ((self.low - self.first_qtr) << 1) & self.max_int
                self.high = (((self.high - self.first_qtr) << 1) | 1) & self.max_int
                bit = self.reader.read_bit() if self.reader.has_more() else 0
                self.value = (((self.value - self.first_qtr) << 1) | bit) & self.max_int
            else:
                break


class ArithmeticAlgorithm(CompressionAlgorithm):
    """
    Arithmetic Coding algorithm supporting both Static and Adaptive modes.
    """

    def __init__(self, adaptive: bool = False):
        self._adaptive = adaptive

    @property
    def algorithm_id(self) -> AlgorithmId:
        return AlgorithmId.ARITHMETIC_ADAPTIVE if self._adaptive else AlgorithmId.ARITHMETIC_STATIC

    @property
    def name(self) -> str:
        return "Arithmetic (Adaptive)" if self._adaptive else "Arithmetic (Static)"

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

        adaptive = config.adaptive if config is not None else self._adaptive
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

        # Chunk input into blocks
        blocks = [data[i:i + block_size] for i in range(0, len(data), block_size)]
        total_symbols = len(blocks)

        # Setup Frequency Table
        if not adaptive:
            # Static model: count actual frequencies
            counts_map = Counter(blocks)
            # Deterministic ordering of symbols
            sorted_symbols = sorted(counts_map.keys())
            counts = [counts_map[sym] for sym in sorted_symbols]
            freq_table = FrequencyTable(sorted_symbols, counts)

            # Serialize model:
            # mode (1B=0), block_size (1B), total_symbols (4B), num_unique (4B)
            # then for each symbol: sym_len (1B) + sym_bytes + count (4B)
            meta = bytearray(struct.pack(">BBII", 0, block_size, total_symbols, len(sorted_symbols)))
            for sym, cnt in zip(sorted_symbols, counts):
                meta.append(len(sym))
                meta.extend(sym)
                meta.extend(struct.pack(">I", cnt))
            model_metadata = bytes(meta)
        else:
            # Adaptive model: alphabet is set of unique symbols
            # Start with uniform counts (or 1 for each unique symbol)
            sorted_symbols = sorted(set(blocks))
            freq_table = FrequencyTable(sorted_symbols, counts=[1] * len(sorted_symbols))

            # Serialize adaptive model header:
            # mode (1B=1), block_size (1B), total_symbols (4B), alphabet_size (4B)
            meta = bytearray(struct.pack(">BBII", 1, block_size, total_symbols, len(sorted_symbols)))
            for sym in sorted_symbols:
                meta.append(len(sym))
                meta.extend(sym)
            model_metadata = bytes(meta)

        # Encode symbols
        encoder = ArithmeticEncoder(precision=32)

        for idx, sym in enumerate(blocks):
            low_c, high_c, tot = freq_table.get_range(sym)

            if record_trace and len(traces) < max_traces:
                traces.append(StepTrace(
                    step_num=idx + 1,
                    description=f"Interval [{low_c}/{tot}, {high_c}/{tot}) for symbol {sym!r}",
                    symbol=sym,
                    state={
                        "low": f"0x{encoder.low:08X}",
                        "high": f"0x{encoder.high:08X}",
                        "low_count": low_c,
                        "high_count": high_c,
                        "total": tot
                    }
                ))

            encoder.encode_symbol(low_c, high_c, tot)

            if adaptive:
                freq_table.increment(sym)

        compressed_payload, _ = encoder.finish()

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

        if len(model_metadata) < 10:
            raise ValueError("Corrupt Arithmetic metadata: header is too short.")

        mode, block_size, total_symbols, num_unique = struct.unpack(">BBII", model_metadata[:10])
        offset = 10

        symbols: List[bytes] = []
        counts: Optional[List[int]] = [] if mode == 0 else None

        for _ in range(num_unique):
            if offset >= len(model_metadata):
                raise ValueError("Corrupt metadata: unexpected end of symbol table.")
            sym_len = model_metadata[offset]
            offset += 1
            sym = model_metadata[offset:offset + sym_len]
            offset += sym_len
            symbols.append(sym)
            if mode == 0:
                cnt = struct.unpack(">I", model_metadata[offset:offset + 4])[0]
                offset += 4
                counts.append(cnt)

        if mode == 0:
            freq_table = FrequencyTable(symbols, counts)
        else:
            freq_table = FrequencyTable(symbols, [1] * len(symbols))

        reader = BitReader(compressed_bytes)
        decoder = ArithmeticDecoder(reader, precision=32)

        output_blocks: List[bytes] = []
        traces: List[StepTrace] = []

        for idx in range(total_symbols):
            tot = freq_table.total
            target_offset = decoder.get_current_offset(tot)
            sym, low_c, high_c = freq_table.get_symbol_at_offset(target_offset)

            output_blocks.append(sym)
            decoder.update_range(low_c, high_c, tot)

            if record_trace and len(traces) < max_traces:
                traces.append(StepTrace(
                    step_num=idx + 1,
                    description=f"Decoded {sym!r} from offset {target_offset}/{tot}",
                    symbol=sym,
                    state={"low_count": low_c, "high_count": high_c, "total": tot}
                ))

            if mode == 1:
                freq_table.increment(sym)

        reconstructed = b"".join(output_blocks)
        if len(reconstructed) != original_size:
            reconstructed = reconstructed[:original_size]

        return DecompressionResult(
            decompressed_bytes=reconstructed,
            original_size=original_size,
            traces=traces
        )
