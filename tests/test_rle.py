"""
Unit tests for RLE and LZW algorithms.
"""

import pytest
from algorithms.rle import RLEAlgorithm
from algorithms.lzw import LZWAlgorithm
from algorithms.base import AlgorithmConfig, AlgorithmId


def test_rle_roundtrip():
    rle = RLEAlgorithm()
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.RLE)

    test_cases = [
        b"",
        b"A",
        b"AAAAAAABBBBBCCCCCDDDDD",
        bytes(range(256)),
        b"Random mixed " + b"X" * 150 + b" followed by non-run text."
    ]

    for data in test_cases:
        res = rle.compress(data, cfg)
        dec = rle.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
        assert dec.decompressed_bytes == data


def test_lzw_roundtrip():
    lzw = LZWAlgorithm()
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.LZW)

    test_cases = [
        b"",
        b"A",
        b"ABABABABABABABABABA",  # Classic KwKwK repetitive pattern
        b"TOBEORNOTTOBEORTOBEORNOT",
        bytes(range(256)),
        "LZW compression test on UTF-8 phrases with repeated substrings.".encode("utf-8") * 4
    ]

    for data in test_cases:
        res = lzw.compress(data, cfg)
        dec = lzw.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
        assert dec.decompressed_bytes == data
