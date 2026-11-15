"""
Unit tests for Static and Adaptive Arithmetic Coding.
"""

import pytest
from algorithms.arithmetic import ArithmeticAlgorithm
from algorithms.base import AlgorithmConfig, AlgorithmId


@pytest.mark.parametrize("adaptive", [False, True])
def test_arithmetic_empty(adaptive):
    algo = ArithmeticAlgorithm(adaptive=adaptive)
    algo_id = AlgorithmId.ARITHMETIC_ADAPTIVE if adaptive else AlgorithmId.ARITHMETIC_STATIC
    cfg = AlgorithmConfig(algorithm_id=algo_id, adaptive=adaptive)
    res = algo.compress(b"", cfg)
    dec = algo.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == b""


@pytest.mark.parametrize("adaptive", [False, True])
def test_arithmetic_single_byte(adaptive):
    algo = ArithmeticAlgorithm(adaptive=adaptive)
    algo_id = AlgorithmId.ARITHMETIC_ADAPTIVE if adaptive else AlgorithmId.ARITHMETIC_STATIC
    cfg = AlgorithmConfig(algorithm_id=algo_id, adaptive=adaptive)
    data = b"Z"
    res = algo.compress(data, cfg)
    dec = algo.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == data


@pytest.mark.parametrize("adaptive", [False, True])
def test_arithmetic_repeated_byte(adaptive):
    algo = ArithmeticAlgorithm(adaptive=adaptive)
    algo_id = AlgorithmId.ARITHMETIC_ADAPTIVE if adaptive else AlgorithmId.ARITHMETIC_STATIC
    cfg = AlgorithmConfig(algorithm_id=algo_id, adaptive=adaptive)
    data = b"M" * 500
    res = algo.compress(data, cfg)
    dec = algo.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == data


@pytest.mark.parametrize("adaptive", [False, True])
def test_arithmetic_arabic_and_binary(adaptive):
    algo = ArithmeticAlgorithm(adaptive=adaptive)
    algo_id = AlgorithmId.ARITHMETIC_ADAPTIVE if adaptive else AlgorithmId.ARITHMETIC_STATIC
    cfg = AlgorithmConfig(algorithm_id=algo_id, adaptive=adaptive)
    data = "ترميز حسابي دقيق للغاية خوارزميات الضغط".encode("utf-8") + bytes(range(64))
    res = algo.compress(data, cfg)
    dec = algo.decompress(res.compressed_bytes, res.model_metadata, res.original_size, cfg)
    assert dec.decompressed_bytes == data
