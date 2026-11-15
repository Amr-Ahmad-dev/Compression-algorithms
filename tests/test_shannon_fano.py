"""
Unit tests for Shannon-Fano algorithm.
"""

import pytest
from algorithms.shannon_fano import ShannonFanoAlgorithm
from algorithms.base import AlgorithmConfig, AlgorithmId


@pytest.fixture
def sf():
    return ShannonFanoAlgorithm()


def test_shannon_fano_empty(sf):
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.SHANNON_FANO)
    res = sf.compress(b"", cfg)
    dec = sf.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == b""


def test_shannon_fano_single_symbol(sf):
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.SHANNON_FANO)
    data = b"K" * 100
    res = sf.compress(data, cfg)
    dec = sf.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == data


@pytest.mark.parametrize("block_size", [1, 2, 3])
def test_shannon_fano_text(sf, block_size):
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.SHANNON_FANO, block_size=block_size)
    data = b"Shannon-Fano coding creates a prefix-free code using recursive partitioning." * 4
    res = sf.compress(data, cfg)
    dec = sf.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == data
