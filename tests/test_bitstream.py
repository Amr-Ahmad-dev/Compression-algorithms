"""
Unit tests for BitWriter and BitReader.
"""

import pytest
from core.bitstream import BitWriter, BitReader


def test_bit_write_read_basic():
    writer = BitWriter()
    writer.write_bit(1)
    writer.write_bit(0)
    writer.write_bit(1)
    writer.write_bit(1)
    writer.write_bit(0)
    writer.write_bit(0)
    writer.write_bit(1)
    writer.write_bit(0)  # 10110010 = 0xB2

    data, padding = writer.flush()
    assert padding == 0
    assert data == bytes([0xB2])

    reader = BitReader(data)
    assert reader.read_bit() == 1
    assert reader.read_bit() == 0
    assert reader.read_bit() == 1
    assert reader.read_bit() == 1
    assert reader.read_bit() == 0
    assert reader.read_bit() == 0
    assert reader.read_bit() == 1
    assert reader.read_bit() == 0
    assert not reader.has_more()


def test_bit_write_read_arbitrary_integers():
    writer = BitWriter()
    writer.write_bits(42, 6)   # 42 in 6 bits: 101010
    writer.write_bits(3, 2)    # 3 in 2 bits: 11 -> Total 10101011 = 0xAB
    writer.write_bits(500, 10) # 10 bits

    data, padding = writer.flush()
    reader = BitReader(data, total_bits=writer.total_bits)

    assert reader.read_bits(6) == 42
    assert reader.read_bits(2) == 3
    assert reader.read_bits(10) == 500


def test_bit_write_bytes_alignment():
    writer = BitWriter()
    writer.write_bit(1)
    writer.write_bytes(b"HELLO")
    writer.write_bit(0)

    data, _ = writer.flush()
    reader = BitReader(data)

    assert reader.read_bit() == 1
    assert reader.read_bytes(5) == b"HELLO"
    assert reader.read_bit() == 0


def test_bit_reader_eof():
    reader = BitReader(b"\x00", total_bits=4)
    for _ in range(4):
        reader.read_bit()
    with pytest.raises(EOFError):
        reader.read_bit()
