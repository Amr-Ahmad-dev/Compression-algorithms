"""
Unit tests for Huffman algorithm across various block sizes and data types.
"""

import pytest
from algorithms.huffman import HuffmanAlgorithm
from algorithms.base import AlgorithmConfig, AlgorithmId


@pytest.fixture
def huffman():
    return HuffmanAlgorithm()


def test_huffman_empty(huffman):
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.HUFFMAN, block_size=1)
    res = huffman.compress(b"", cfg)
    dec = huffman.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == b""


def test_huffman_single_byte(huffman):
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.HUFFMAN, block_size=1)
    data = b"X"
    res = huffman.compress(data, cfg)
    dec = huffman.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == data


def test_huffman_repeated_byte(huffman):
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.HUFFMAN, block_size=1)
    data = b"A" * 1000
    res = huffman.compress(data, cfg)
    dec = huffman.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == data


def test_huffman_all_256_bytes(huffman):
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.HUFFMAN, block_size=1)
    data = bytes(range(256))
    res = huffman.compress(data, cfg)
    dec = huffman.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == data


@pytest.mark.parametrize("block_size", [1, 2, 3, 4])
def test_huffman_block_sizes(huffman, block_size):
    data = ("اختبار دقة ضغط هوفمان متعدد الأحجام والتطابقات " * 5).encode("utf-8")
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.HUFFMAN, block_size=block_size)
    res = huffman.compress(data, cfg)
    dec = huffman.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == data
