"""
Base classes and interfaces for compression algorithms.
All algorithms must strictly follow this contract and return exact data upon decompression.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Any, List, Optional, Tuple


class AlgorithmId(IntEnum):
    HUFFMAN = 1
    ARITHMETIC_STATIC = 2
    ARITHMETIC_ADAPTIVE = 3
    SHANNON_FANO = 4
    LZW = 5
    RLE = 6
    DELTA_HUFFMAN = 7


@dataclass
class AlgorithmConfig:
    algorithm_id: AlgorithmId
    block_size: int = 1  # 1 for byte-level, 2..4 for block-level
    precision_bits: int = 32  # for arithmetic coding
    adaptive: bool = False
    max_dict_size: int = 4096  # for LZW
    rle_escape_byte: int = 0xAA  # for RLE
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepTrace:
    """Educational step record for visualizing encoding/decoding."""
    step_num: int
    description: str
    symbol: Optional[Any] = None
    codeword: Optional[str] = None
    state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompressionResult:
    compressed_bytes: bytes
    model_metadata: bytes
    original_size: int
    compressed_payload_size: int
    total_model_size: int
    block_size: int
    algorithm_id: AlgorithmId
    traces: List[StepTrace] = field(default_factory=list)


@dataclass
class DecompressionResult:
    decompressed_bytes: bytes
    original_size: int
    traces: List[StepTrace] = field(default_factory=list)


class CompressionAlgorithm(ABC):
    """Abstract base class for all compression algorithms."""

    @property
    @abstractmethod
    def algorithm_id(self) -> AlgorithmId:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def compress(
        self,
        data: bytes,
        config: Optional[AlgorithmConfig] = None,
        record_trace: bool = False,
        max_traces: int = 100
    ) -> CompressionResult:
        """Compress raw bytes into compressed payload and model metadata."""
        pass

    @abstractmethod
    def decompress(
        self,
        compressed_bytes: bytes,
        model_metadata: bytes,
        original_size: int,
        config: Optional[AlgorithmConfig] = None,
        record_trace: bool = False,
        max_traces: int = 100
    ) -> DecompressionResult:
        """Decompress payload back into exact original bytes using metadata."""
        pass
