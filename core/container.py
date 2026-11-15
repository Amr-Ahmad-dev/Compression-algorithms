"""
Binary Container Format for the Compression Laboratory (.clab).
Provides self-contained packaging, versioning, integrity verification (CRC32),
and recursive directory archive serialization with strict security checks against path traversal.
"""

import os
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from algorithms.base import AlgorithmId, AlgorithmConfig, CompressionResult
from algorithms import get_algorithm


# 4-byte ASCII magic identifier
MAGIC = b"CLAB"
FORMAT_VERSION = 1

class SecurityError(Exception):
    """Raised when an archive contains an invalid or malicious path."""
    pass

# Flag bits
FLAG_IS_ARCHIVE = 1 << 0
FLAG_DELTA_APPLIED = 1 << 1


@dataclass
class ContainerMetadata:
    version: int
    algorithm_id: AlgorithmId
    flags: int
    original_size: int
    original_crc32: int
    filename: str
    block_size: int
    model_metadata: bytes
    is_archive: bool = False


@dataclass
class ArchiveEntry:
    is_dir: bool
    rel_path: str
    data: bytes = b""


def pack_directory(folder_path: Union[str, Path]) -> bytes:
    """
    Serializes a folder into an archive byte stream:
    - total_entries (uint32 BE)
    - for each entry:
      - is_dir (uint8: 1 if dir, 0 if file)
      - path_len (uint16 BE)
      - rel_path (UTF-8 bytes)
      - data_len (uint64 BE)
      - data_bytes
    """
    folder = Path(folder_path).resolve()
    if not folder.is_dir():
        raise ValueError(f"Path '{folder_path}' is not a directory.")

    entries: List[ArchiveEntry] = []

    for root, dirs, files in os.walk(folder):
        rel_root = os.path.relpath(root, folder).replace("\\", "/")
        if rel_root != ".":
            # Add directory entry
            entries.append(ArchiveEntry(is_dir=True, rel_path=rel_root))

        for file in files:
            full_path = os.path.join(root, file)
            rel_file = os.path.relpath(full_path, folder).replace("\\", "/")
            try:
                with open(full_path, "rb") as f:
                    file_bytes = f.read()
                entries.append(ArchiveEntry(is_dir=False, rel_path=rel_file, data=file_bytes))
            except Exception as e:
                raise IOError(f"Error reading file '{full_path}' for archive: {e}")

    buf = bytearray()
    buf.extend(struct.pack(">I", len(entries)))

    for entry in entries:
        path_bytes = entry.rel_path.encode("utf-8")
        buf.append(1 if entry.is_dir else 0)
        buf.extend(struct.pack(">H", len(path_bytes)))
        buf.extend(path_bytes)
        buf.extend(struct.pack(">Q", len(entry.data)))
        if entry.data:
            buf.extend(entry.data)

    return bytes(buf)


def unpack_directory(archive_bytes: bytes, destination_dir: Union[str, Path]) -> List[str]:
    """
    Unpacks archive bytes into destination folder with path traversal protection.
    Returns list of extracted relative paths.
    """
    dest = Path(destination_dir).resolve()
    os.makedirs(dest, exist_ok=True)

    if len(archive_bytes) < 4:
        raise ValueError("Archive data too short to contain header.")

    total_entries = struct.unpack(">I", archive_bytes[:4])[0]
    offset = 4
    extracted_paths: List[str] = []

    for _ in range(total_entries):
        if offset + 3 > len(archive_bytes):
            raise ValueError("Corrupt archive: unexpected end of stream.")
        is_dir = bool(archive_bytes[offset])
        offset += 1
        path_len = struct.unpack(">H", archive_bytes[offset:offset + 2])[0]
        offset += 2
        if offset + path_len > len(archive_bytes):
            raise ValueError("Corrupt archive: invalid path length.")
        rel_path = archive_bytes[offset:offset + path_len].decode("utf-8")
        offset += path_len

        # Path traversal security check
        target_path = (dest / rel_path).resolve()
        if not str(target_path).startswith(str(dest)):
            raise SecurityError(f"Malicious path traversal detected in archive: {rel_path}")

        data_len = struct.unpack(">Q", archive_bytes[offset:offset + 8])[0]
        offset += 8
        if offset + data_len > len(archive_bytes):
            raise ValueError("Corrupt archive: file data truncated.")
        file_data = archive_bytes[offset:offset + data_len]
        offset += data_len

        if is_dir:
            os.makedirs(target_path, exist_ok=True)
        else:
            os.makedirs(target_path.parent, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(file_data)

        extracted_paths.append(rel_path)

    return extracted_paths


def build_container(
    result: CompressionResult,
    original_data: bytes,
    original_filename: str,
    is_archive: bool = False
) -> bytes:
    """
    Packages compressed payload and model metadata into a self-contained .clab file.

    Header structure:
    - MAGIC: 4 bytes ("CLAB")
    - VERSION: 1 byte (uint8)
    - ALGORITHM_ID: 1 byte (uint8)
    - FLAGS: 2 bytes (uint16 BE)
    - BLOCK_SIZE: 1 byte (uint8)
    - ORIGINAL_SIZE: 8 bytes (uint64 BE)
    - CRC32: 4 bytes (uint32 BE)
    - FILENAME_LEN: 2 bytes (uint16 BE)
    - FILENAME: UTF-8 bytes
    - MODEL_METADATA_LEN: 4 bytes (uint32 BE)
    - MODEL_METADATA: raw bytes
    - PAYLOAD_LEN: 8 bytes (uint64 BE)
    - PAYLOAD: raw compressed bytes
    """
    flags = 0
    if is_archive:
        flags |= FLAG_IS_ARCHIVE
    if result.algorithm_id == AlgorithmId.DELTA_HUFFMAN:
        flags |= FLAG_DELTA_APPLIED

    crc = zlib.crc32(original_data) & 0xFFFFFFFF
    fname_bytes = original_filename.encode("utf-8")

    buf = bytearray()
    buf.extend(MAGIC)
    buf.append(FORMAT_VERSION)
    buf.append(int(result.algorithm_id))
    buf.extend(struct.pack(">HB", flags, result.block_size))
    buf.extend(struct.pack(">QI", len(original_data), crc))
    buf.extend(struct.pack(">H", len(fname_bytes)))
    buf.extend(fname_bytes)
    buf.extend(struct.pack(">I", len(result.model_metadata)))
    buf.extend(result.model_metadata)
    buf.extend(struct.pack(">Q", len(result.compressed_bytes)))
    buf.extend(result.compressed_bytes)

    return bytes(buf)


def parse_container(container_bytes: bytes) -> Tuple[ContainerMetadata, bytes]:
    """
    Parses and validates a .clab file container.
    Returns (ContainerMetadata, compressed_payload).
    """
    if len(container_bytes) < 23:
        raise ValueError("File is too small to be a valid Compression Laboratory container.")

    # 1. Verify Magic Header
    if container_bytes[:4] != MAGIC:
        raise ValueError(f"Invalid magic header: expected {MAGIC!r}, got {container_bytes[:4]!r}")

    version = container_bytes[4]
    if version != FORMAT_VERSION:
        raise ValueError(f"Unsupported container version: {version} (expected {FORMAT_VERSION})")

    algo_id_int = container_bytes[5]
    try:
        algo_id = AlgorithmId(algo_id_int)
    except ValueError:
        raise ValueError(f"Unknown algorithm ID in container: {algo_id_int}")

    flags, block_size = struct.unpack(">HB", container_bytes[6:9])
    orig_size, crc32 = struct.unpack(">QI", container_bytes[9:21])
    fname_len = struct.unpack(">H", container_bytes[21:23])[0]

    offset = 23
    if offset + fname_len > len(container_bytes):
        raise ValueError("Corrupt container: filename length exceeds file boundary.")

    filename = container_bytes[offset:offset + fname_len].decode("utf-8", errors="replace")
    offset += fname_len

    if offset + 4 > len(container_bytes):
        raise ValueError("Corrupt container: missing model metadata length.")
    model_len = struct.unpack(">I", container_bytes[offset:offset + 4])[0]
    offset += 4

    if offset + model_len > len(container_bytes):
        raise ValueError("Corrupt container: model metadata length exceeds file boundary.")
    model_metadata = container_bytes[offset:offset + model_len]
    offset += model_len

    if offset + 8 > len(container_bytes):
        raise ValueError("Corrupt container: missing payload length.")
    payload_len = struct.unpack(">Q", container_bytes[offset:offset + 8])[0]
    offset += 8

    if offset + payload_len > len(container_bytes):
        raise ValueError("Corrupt container: payload length exceeds file boundary.")
    payload = container_bytes[offset:offset + payload_len]

    metadata = ContainerMetadata(
        version=version,
        algorithm_id=algo_id,
        flags=flags,
        original_size=orig_size,
        original_crc32=crc32,
        filename=filename,
        block_size=block_size,
        model_metadata=model_metadata,
        is_archive=bool(flags & FLAG_IS_ARCHIVE)
    )

    return metadata, payload


def decompress_container(
    container_bytes: bytes,
    verify_checksum: bool = True
) -> Tuple[ContainerMetadata, bytes]:
    """
    Fully self-contained decompression of a .clab file without needing external parameters.
    Verifies original CRC32 checksum and original size.
    """
    metadata, payload = parse_container(container_bytes)
    algo = get_algorithm(metadata.algorithm_id)

    config = AlgorithmConfig(
        algorithm_id=metadata.algorithm_id,
        block_size=metadata.block_size
    )

    res = algo.decompress(
        compressed_bytes=payload,
        model_metadata=metadata.model_metadata,
        original_size=metadata.original_size,
        config=config
    )

    decompressed_data = res.decompressed_bytes

    if len(decompressed_data) != metadata.original_size:
        raise ValueError(
            f"Size mismatch: expected {metadata.original_size} bytes, got {len(decompressed_data)} bytes."
        )

    if verify_checksum:
        actual_crc = zlib.crc32(decompressed_data) & 0xFFFFFFFF
        if actual_crc != metadata.original_crc32:
            raise ValueError(
                f"Data corruption detected! CRC32 mismatch: expected 0x{metadata.original_crc32:08X}, "
                f"computed 0x{actual_crc:08X}."
            )

    return metadata, decompressed_data
