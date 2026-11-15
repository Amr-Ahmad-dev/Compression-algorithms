"""
Edge cases and security reliability tests.
Tests corruption detection, malicious archive paths, empty files, large data, Arabic text.
"""

import pytest
from core.container import (
    build_container,
    parse_container,
    decompress_container,
    unpack_directory,
    MAGIC,
    SecurityError
)
from algorithms import get_algorithm, AlgorithmId
from algorithms.base import AlgorithmConfig


def test_malicious_path_traversal_protection(tmp_path):
    """Verifies that an archive containing relative path '../evil.txt' is rejected."""
    import struct
    buf = bytearray()
    buf.extend(struct.pack(">I", 1))  # 1 entry
    buf.append(0)  # is_file
    malicious_path = "../evil.txt".encode("utf-8")
    buf.extend(struct.pack(">H", len(malicious_path)))
    buf.extend(malicious_path)
    buf.extend(struct.pack(">Q", 4))
    buf.extend(b"EVIL")

    dest = tmp_path / "sandbox"
    dest.mkdir()

    with pytest.raises(SecurityError, match="Malicious path traversal"):
        unpack_directory(bytes(buf), dest)


def test_invalid_magic_header():
    fake_data = b"NOT_MAGIC" + b"\x00" * 30
    with pytest.raises(ValueError, match="Invalid magic header"):
        parse_container(fake_data)


def test_truncated_container():
    algo = get_algorithm(AlgorithmId.HUFFMAN)
    data = b"Testing truncation detection"
    res = algo.compress(data, AlgorithmConfig(algorithm_id=AlgorithmId.HUFFMAN))
    clab = build_container(res, data, "trunc.txt")

    # Truncate by 10 bytes
    truncated = clab[:-10]
    with pytest.raises(ValueError):
        parse_container(truncated)


@pytest.mark.parametrize("algo_id", [
    AlgorithmId.HUFFMAN,
    AlgorithmId.ARITHMETIC_STATIC,
    AlgorithmId.ARITHMETIC_ADAPTIVE,
    AlgorithmId.SHANNON_FANO,
    AlgorithmId.LZW,
    AlgorithmId.RLE,
    AlgorithmId.DELTA_HUFFMAN
])
def test_all_algorithms_arabic_utf8_invariance(algo_id):
    """Invariant: decompress(compress(data)) == data for Arabic and Unicode text."""
    arabic_text = (
        "مختبر ضغط البيانات والمعلوماتية: دراسة نظرية شانون للإنتروبيا والتشفير الخالي من الفقد. "
        "الترميز الحسابي وترميز هوفمان وشانون فانو وقواميس ليمبل زيف ولش."
    ).encode("utf-8")

    algo = get_algorithm(algo_id)
    cfg = AlgorithmConfig(algorithm_id=algo_id)
    res = algo.compress(arabic_text, cfg)
    clab = build_container(res, arabic_text, "arabic.txt")

    meta, decomp = decompress_container(clab, verify_checksum=True)
    assert decomp == arabic_text
    assert meta.filename == "arabic.txt"
