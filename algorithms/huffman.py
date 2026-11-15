"""
Huffman Encoding and Decoding Implementation from scratch.
Supports:
- Byte-level and configurable block-level symbols (1, 2, 3, 4 bytes, etc.).
- Complete handling of incomplete final blocks.
- Deterministic priority queue tie-breaking.
- Compact tree serialization and reconstruction.
- Step-by-step tracing for educational inspection.
- Edge cases: empty data, single unique symbol, uniform frequencies.
"""

import heapq
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


class HuffmanNode:
    """Node in the Huffman coding tree."""
    __slots__ = ('symbol', 'weight', 'left', 'right', 'seq')

    def __init__(
        self,
        weight: int,
        symbol: Optional[bytes] = None,
        left: Optional['HuffmanNode'] = None,
        right: Optional['HuffmanNode'] = None,
        seq: int = 0
    ):
        self.weight = weight
        self.symbol = symbol
        self.left = left
        self.right = right
        self.seq = seq  # Deterministic tie-breaker counter

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    def __lt__(self, other: 'HuffmanNode') -> bool:
        if self.weight != other.weight:
            return self.weight < other.weight
        # Deterministic secondary tie-breaker:
        # Leaves sort before internal nodes; if both are leaves, compare symbol bytes.
        if self.is_leaf and not other.is_leaf:
            return True
        if not self.is_leaf and other.is_leaf:
            return False
        if self.is_leaf and other.is_leaf:
            return (self.symbol or b'') < (other.symbol or b'')
        return self.seq < other.seq


def chunk_data_into_blocks(data: bytes, block_size: int) -> List[bytes]:
    """Divides byte data into blocks of up to block_size bytes."""
    if block_size < 1:
        raise ValueError(f"block_size must be >= 1, got {block_size}")
    if not data:
        return []
    return [data[i:i + block_size] for i in range(0, len(data), block_size)]


def build_huffman_tree(frequencies: Dict[bytes, int]) -> Optional[HuffmanNode]:
    """
    Constructs a deterministic Huffman tree from symbol frequencies.
    Uses a priority queue with deterministic tie-breaking.
    """
    if not frequencies:
        return None

    heap: List[HuffmanNode] = []
    seq = 0

    # Sort symbols deterministically before pushing to heap
    sorted_items = sorted(frequencies.items(), key=lambda x: (x[1], x[0]))

    for symbol, weight in sorted_items:
        seq += 1
        heapq.heappush(heap, HuffmanNode(weight=weight, symbol=symbol, seq=seq))

    # Single unique symbol edge case: the tree is simply the single leaf
    if len(heap) == 1:
        return heap[0]

    # Standard two-minimum combine
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        seq += 1
        merged = HuffmanNode(
            weight=left.weight + right.weight,
            left=left,
            right=right,
            seq=seq
        )
        heapq.heappush(heap, merged)

    return heap[0]


def generate_codewords(root: Optional[HuffmanNode]) -> Dict[bytes, str]:
    """
    Traverses the tree to generate prefix-free binary codes for each symbol.
    Left branch = '0', Right branch = '1'.
    """
    codewords: Dict[bytes, str] = {}
    if not root:
        return codewords

    def traverse(node: HuffmanNode, current_code: str) -> None:
        if node.is_leaf:
            codewords[node.symbol or b''] = current_code if current_code else "0"
            return
        if node.left:
            traverse(node.left, current_code + "0")
        if node.right:
            traverse(node.right, current_code + "1")

    traverse(root, "")
    return codewords


def serialize_tree(root: Optional[HuffmanNode]) -> bytes:
    """
    Serializes a Huffman tree using pre-order bit traversal:
    - Internal node: bit '1'
    - Leaf node: bit '0' followed by 8-bit symbol length, followed by symbol raw bytes.
    """
    if not root:
        return b""

    writer = BitWriter()

    def write_node(node: Optional[HuffmanNode]) -> None:
        if node is None:
            return
        if node.is_leaf:
            writer.write_bit(0)
            sym = node.symbol or b""
            writer.write_bits(len(sym), 8)
            writer.write_bytes(sym)
        else:
            writer.write_bit(1)
            write_node(node.left)
            write_node(node.right)

    write_node(root)
    tree_bytes, _ = writer.flush()
    return tree_bytes


def deserialize_tree(tree_data: bytes) -> Optional[HuffmanNode]:
    """Reconstructs the Huffman tree from serialized pre-order bitstream."""
    if not tree_data:
        return None

    reader = BitReader(tree_data)

    def read_node() -> Optional[HuffmanNode]:
        if not reader.has_more():
            return None
        is_internal = reader.read_bit()
        if is_internal == 0:
            sym_len = reader.read_bits(8)
            sym = reader.read_bytes(sym_len)
            return HuffmanNode(weight=0, symbol=sym)
        else:
            left = read_node()
            right = read_node()
            return HuffmanNode(weight=0, left=left, right=right)

    return read_node()


def render_ascii_tree(root: Optional[HuffmanNode], max_depth: int = 6) -> str:
    """Generates a clean ASCII representation of the Huffman tree for education/UI."""
    if not root:
        return "<Empty Tree>"

    lines: List[str] = []

    def _format_symbol(sym: Optional[bytes]) -> str:
        if sym is None:
            return ""
        if len(sym) == 1:
            b = sym[0]
            if 32 <= b <= 126:
                return f"'{chr(b)}' (0x{b:02X})"
            return f"0x{b:02X}"
        return f"[{sym.hex()}]"

    def recurse(node: Optional[HuffmanNode], prefix: str, is_tail: bool, depth: int) -> None:
        if node is None or depth > max_depth:
            if depth > max_depth and node is not None:
                lines.append(prefix + ("└── " if is_tail else "├── ") + "...")
            return

        connector = "└── " if is_tail else "├── "
        if node.is_leaf:
            lines.append(f"{prefix}{connector}Leaf: {_format_symbol(node.symbol)} [weight={node.weight}]")
        else:
            lines.append(f"{prefix}{connector}Node [weight={node.weight}]")
            child_prefix = prefix + ("    " if is_tail else "│   ")
            recurse(node.left, child_prefix, False, depth + 1)
            recurse(node.right, child_prefix, True, depth + 1)

    recurse(root, "", True, 0)
    return "\n".join(lines)


class HuffmanAlgorithm(CompressionAlgorithm):
    """
    Huffman compression implementation with configurable block size,
    complete deterministic tree handling, and full transparency tracing.
    """

    @property
    def algorithm_id(self) -> AlgorithmId:
        return AlgorithmId.HUFFMAN

    @property
    def name(self) -> str:
        return "Huffman"

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

        # 1. Chunking into blocks
        blocks = chunk_data_into_blocks(data, block_size)
        total_symbols = len(blocks)

        # 2. Frequency counting
        freq: Dict[bytes, int] = Counter(blocks)

        # 3. Build tree and generate codewords
        root = build_huffman_tree(freq)
        codewords = generate_codewords(root)

        # 4. Serialize tree into model metadata
        # Header for metadata: block_size (uint8), total_symbols (uint32 BE), serialized_tree
        raw_tree_bytes = serialize_tree(root)
        import struct
        model_metadata = struct.pack(">BI", block_size, total_symbols) + raw_tree_bytes

        # 5. Encode symbols into bitstream
        writer = BitWriter()
        for idx, block in enumerate(blocks):
            code = codewords[block]
            writer.write_bitstring(code)

            if record_trace and len(traces) < max_traces:
                traces.append(StepTrace(
                    step_num=idx + 1,
                    description=f"Encoded block {block!r} -> {code}",
                    symbol=block,
                    codeword=code,
                    state={"remaining_symbols": total_symbols - idx - 1}
                ))

        compressed_payload, _ = writer.flush()

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

        import struct
        if len(model_metadata) < 5:
            raise ValueError("Corrupt Huffman metadata: header is too short.")

        block_size, total_symbols = struct.unpack(">BI", model_metadata[:5])
        tree_bytes = model_metadata[5:]

        root = deserialize_tree(tree_bytes)
        if not root:
            raise ValueError("Failed to deserialize Huffman tree from metadata.")

        reader = BitReader(compressed_bytes)
        output_blocks: List[bytes] = []
        traces: List[StepTrace] = []

        curr = root
        symbols_decoded = 0

        # Special single leaf case
        if curr.is_leaf:
            single_sym = curr.symbol or b""
            output_data = single_sym * total_symbols
            return DecompressionResult(
                decompressed_bytes=output_data[:original_size],
                original_size=original_size
            )

        while symbols_decoded < total_symbols and reader.has_more():
            bit = reader.read_bit()
            curr = curr.right if bit else curr.left

            if curr is None:
                raise ValueError("Corrupt Huffman stream: reached invalid tree branch.")

            if curr.is_leaf:
                sym = curr.symbol or b""
                output_blocks.append(sym)
                symbols_decoded += 1

                if record_trace and len(traces) < max_traces:
                    traces.append(StepTrace(
                        step_num=symbols_decoded,
                        description=f"Decoded symbol {sym!r}",
                        symbol=sym,
                        state={"symbols_decoded": symbols_decoded, "total": total_symbols}
                    ))

                curr = root  # Reset to root for next symbol

        reconstructed = b"".join(output_blocks)
        if len(reconstructed) != original_size:
            # Handle truncation or exact size
            reconstructed = reconstructed[:original_size]

        return DecompressionResult(
            decompressed_bytes=reconstructed,
            original_size=original_size,
            traces=traces
        )
