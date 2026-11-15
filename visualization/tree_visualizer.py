"""
Visualizer for Compression Data Structures and Intermediate States.
Generates clear textual and ASCII visual representations of:
1. Huffman trees
2. Shannon-Fano partition trees
3. Arithmetic coding interval narrowing
"""

from typing import Dict, List, Optional, Tuple, Any
from algorithms.huffman import HuffmanNode, render_ascii_tree


def format_byte(b: int) -> str:
    """Formats a byte value into printable representation or hex."""
    if 32 <= b <= 126:
        return f"'{chr(b)}'"
    return f"0x{b:02X}"


def format_symbol(sym: bytes) -> str:
    """Formats bytes symbol into readable string."""
    if len(sym) == 1:
        return format_byte(sym[0])
    return f"b'{sym.decode('latin1', errors='replace')}'"


def render_shannon_fano_partitions(partitions: List[Dict[str, Any]]) -> str:
    """
    Renders the recursive Shannon-Fano partition sequence as a clean tree.
    """
    if not partitions:
        return "<No Partitions Recorded>"

    lines: List[str] = ["Shannon-Fano Recursive Partitioning:"]
    for p in partitions:
        depth = p.get("depth", 0)
        indent = "  " * depth
        left_syms = [format_symbol(s) for s in p.get("left_symbols", [])[:5]]
        right_syms = [format_symbol(s) for s in p.get("right_symbols", [])[:5]]
        w_left = p.get("left_weight", 0)
        w_right = p.get("right_weight", 0)

        lines.append(
            f"{indent}├── [0] {len(p['left_symbols'])} syms (wt={w_left}): {', '.join(left_syms)}..."
        )
        lines.append(
            f"{indent}└── [1] {len(p['right_symbols'])} syms (wt={w_right}): {', '.join(right_syms)}..."
        )

    return "\n".join(lines)


def render_arithmetic_interval_steps(traces: List[Any], max_steps: int = 15) -> str:
    """
    Formats arithmetic coding interval steps showing bounds narrowing.
    """
    if not traces:
        return "<No Arithmetic Trace Available>"

    lines: List[str] = [
        f"{'Step':<5} | {'Symbol':<8} | {'Interval Range':<24} | {'Low (Hex)':<12} | {'High (Hex)':<12}",
        "-" * 72
    ]

    for t in traces[:max_steps]:
        sym = format_symbol(t.symbol) if t.symbol else "?"
        low_c = t.state.get("low_count", 0)
        high_c = t.state.get("high_count", 0)
        tot = t.state.get("total", 1)
        low_hex = t.state.get("low", "0x00000000")
        high_hex = t.state.get("high", "0xFFFFFFFF")

        frac_str = f"[{low_c}/{tot}, {high_c}/{tot})"
        lines.append(f"{t.step_num:<5} | {sym:<8} | {frac_str:<24} | {low_hex:<12} | {high_hex:<12}")

    if len(traces) > max_steps:
        lines.append(f"... (+ {len(traces) - max_steps} more steps)")

    return "\n".join(lines)
