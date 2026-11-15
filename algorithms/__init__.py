"""
Algorithms module registry and exports.
"""

from algorithms.base import (
    CompressionAlgorithm,
    AlgorithmId,
    AlgorithmConfig,
    CompressionResult,
    DecompressionResult,
    StepTrace
)
from algorithms.huffman import HuffmanAlgorithm
from algorithms.arithmetic import ArithmeticAlgorithm
from algorithms.shannon_fano import ShannonFanoAlgorithm
from algorithms.rle import RLEAlgorithm
from algorithms.lzw import LZWAlgorithm
from algorithms.delta import DeltaHuffmanAlgorithm

ALGORITHM_REGISTRY = {
    AlgorithmId.HUFFMAN: HuffmanAlgorithm(),
    AlgorithmId.ARITHMETIC_STATIC: ArithmeticAlgorithm(adaptive=False),
    AlgorithmId.ARITHMETIC_ADAPTIVE: ArithmeticAlgorithm(adaptive=True),
    AlgorithmId.SHANNON_FANO: ShannonFanoAlgorithm(),
    AlgorithmId.LZW: LZWAlgorithm(),
    AlgorithmId.RLE: RLEAlgorithm(),
    AlgorithmId.DELTA_HUFFMAN: DeltaHuffmanAlgorithm(),
}


def get_algorithm(algo_id: AlgorithmId) -> CompressionAlgorithm:
    if algo_id not in ALGORITHM_REGISTRY:
        raise ValueError(f"Unknown algorithm ID: {algo_id}")
    return ALGORITHM_REGISTRY[algo_id]
