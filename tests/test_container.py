"""
Tests for Container format, Archive Packing, and Directory Extraction.
"""

import os
import tempfile
import pytest
from core.container import (
    build_container,
    parse_container,
    decompress_container,
    pack_directory,
    unpack_directory
)
from algorithms import get_algorithm, AlgorithmId
from algorithms.base import AlgorithmConfig


def test_container_checksum_verification():
    algo = get_algorithm(AlgorithmId.HUFFMAN)
    data = b"Testing CRC32 verification integrity in container."
    cfg = AlgorithmConfig(algorithm_id=AlgorithmId.HUFFMAN)
    res = algo.compress(data, cfg)

    clab_bytes = bytearray(build_container(res, data, "test.txt"))

    # Verify normal decompression succeeds
    meta, decomp = decompress_container(bytes(clab_bytes))
    assert decomp == data

    # Corrupt payload: flip a byte in payload
    clab_bytes[-1] ^= 0xFF
    with pytest.raises(Exception):
        decompress_container(bytes(clab_bytes), verify_checksum=True)


def test_folder_pack_unpack_hierarchy():
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dest_dir:
        # Create hierarchy
        os.makedirs(os.path.join(src_dir, "dir1", "dir2"), exist_ok=True)
        os.makedirs(os.path.join(src_dir, "empty_dir"), exist_ok=True)

        with open(os.path.join(src_dir, "root.txt"), "w") as f:
            f.write("root file")
        with open(os.path.join(src_dir, "dir1", "dir2", "leaf.bin"), "wb") as f:
            f.write(bytes([1, 2, 3, 4, 5]))

        arch_bytes = pack_directory(src_dir)
        algo = get_algorithm(AlgorithmId.HUFFMAN)
        res = algo.compress(arch_bytes, AlgorithmConfig(algorithm_id=AlgorithmId.HUFFMAN))
        clab = build_container(res, arch_bytes, "archive", is_archive=True)

        meta, decomp = decompress_container(clab)
        assert meta.is_archive is True
        extracted = unpack_directory(decomp, dest_dir)

        assert os.path.exists(os.path.join(dest_dir, "root.txt"))
        assert os.path.exists(os.path.join(dest_dir, "empty_dir"))
        assert os.path.exists(os.path.join(dest_dir, "dir1", "dir2", "leaf.bin"))
