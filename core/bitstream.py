"""
Bitstream I/O module for arbitrary-precision bit manipulation.
Provides BitWriter and BitReader for packing and unpacking bits into bytes.
"""

from typing import Tuple, List, Union


class BitWriter:
    """
    Accumulates individual bits and variable-length bitfields into a byte buffer.
    """
    def __init__(self):
        self._buffer = bytearray()
        self._current_byte = 0
        self._bit_count = 0  # Number of bits in current_byte (0..7)
        self._total_bits = 0

    def write_bit(self, bit: int) -> None:
        """Write a single bit (0 or 1)."""
        bit = 1 if bit else 0
        self._current_byte = (self._current_byte << 1) | bit
        self._bit_count += 1
        self._total_bits += 1

        if self._bit_count == 8:
            self._buffer.append(self._current_byte)
            self._current_byte = 0
            self._bit_count = 0

    def write_bits(self, value: int, num_bits: int) -> None:
        """
        Write `num_bits` from `value`, starting from the most significant bit.
        """
        if num_bits < 0:
            raise ValueError(f"num_bits must be non-negative, got {num_bits}")
        for i in range(num_bits - 1, -1, -1):
            self.write_bit((value >> i) & 1)

    def write_bitstring(self, bitstr: str) -> None:
        """Write a string of '0's and '1's."""
        for char in bitstr:
            if char == '0':
                self.write_bit(0)
            elif char == '1':
                self.write_bit(1)
            else:
                raise ValueError(f"Invalid character in bitstring: {char}")

    def write_bytes(self, data: bytes) -> None:
        """Write raw bytes into the stream. If aligned, appends directly."""
        if self._bit_count == 0:
            self._buffer.extend(data)
            self._total_bits += len(data) * 8
        else:
            for byte in data:
                self.write_bits(byte, 8)

    def flush(self) -> Tuple[bytes, int]:
        """
        Pad the current byte with zeros if incomplete and return the byte buffer
        along with the number of padding bits added (0..7).
        """
        padding_bits = 0
        if self._bit_count > 0:
            padding_bits = 8 - self._bit_count
            self._current_byte <<= padding_bits
            self._buffer.append(self._current_byte)
            self._current_byte = 0
            self._bit_count = 0
            self._total_bits += padding_bits
        return bytes(self._buffer), padding_bits

    def get_bytes(self) -> bytes:
        """Flush and return bytes."""
        data, _ = self.flush()
        return data

    @property
    def total_bits(self) -> int:
        return self._total_bits


class BitReader:
    """
    Reads individual bits and variable-length bitfields from a byte buffer.
    """
    def __init__(self, data: bytes, total_bits: int = -1):
        self._data = memoryview(data)
        self._byte_pos = 0
        self._bit_pos = 0  # 0 is MSB of current byte, 7 is LSB
        self._data_len = len(data)
        if total_bits >= 0:
            self._total_bits = min(total_bits, self._data_len * 8)
        else:
            self._total_bits = self._data_len * 8
        self._bits_read = 0

    def read_bit(self) -> int:
        """Read a single bit (0 or 1). Raises EOFError if stream exhausted."""
        if self._bits_read >= self._total_bits or self._byte_pos >= self._data_len:
            raise EOFError("End of bitstream reached")

        byte = self._data[self._byte_pos]
        bit = (byte >> (7 - self._bit_pos)) & 1

        self._bit_pos += 1
        self._bits_read += 1
        if self._bit_pos == 8:
            self._bit_pos = 0
            self._byte_pos += 1

        return bit

    def read_bits(self, num_bits: int) -> int:
        """Read `num_bits` as an unsigned integer."""
        if num_bits < 0:
            raise ValueError(f"num_bits must be non-negative, got {num_bits}")
        value = 0
        for _ in range(num_bits):
            value = (value << 1) | self.read_bit()
        return value

    def read_bitstring(self, num_bits: int) -> str:
        """Read `num_bits` as a string of '0's and '1's."""
        chars = []
        for _ in range(num_bits):
            chars.append('1' if self.read_bit() else '0')
        return "".join(chars)

    def read_bytes(self, num_bytes: int) -> bytes:
        """Read `num_bytes` of raw data."""
        if self._bit_pos == 0:
            end_pos = self._byte_pos + num_bytes
            if end_pos > self._data_len:
                raise EOFError("End of byte stream reached")
            res = bytes(self._data[self._byte_pos:end_pos])
            self._byte_pos = end_pos
            self._bits_read += num_bytes * 8
            return res
        else:
            out = bytearray(num_bytes)
            for i in range(num_bytes):
                out[i] = self.read_bits(8)
            return bytes(out)

    def has_more(self) -> bool:
        """Check if more bits remain to be read."""
        return self._bits_read < self._total_bits and self._byte_pos < self._data_len

    @property
    def bits_remaining(self) -> int:
        return max(0, self._total_bits - self._bits_read)
