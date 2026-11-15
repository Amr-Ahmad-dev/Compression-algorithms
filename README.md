# 🔬 Antigravity File Compression Laboratory

A comprehensive, functional, educational, and visually appealing **File Compression Laboratory** built from scratch in Python.

This laboratory provides an interactive research environment to study, implement, visualize, compare, and benchmark lossless data compression algorithms while understanding the fundamental mathematical relationships between probability distributions, Shannon entropy, autocorrelation, and compressibility.

---

## ⚡ Non-Negotiable Core Principle
**Every compression and decompression algorithm in this laboratory is implemented strictly from scratch.**
No external compression libraries (such as `gzip`, `zlib`, `bz2`, `lzma`, or third-party Huffman/Arithmetic wrappers) are used for any algorithm. All trees, priority queues, bitstreams, interval subdivisions, and codebooks are custom-built.

---

## 📐 Mathematical Foundations

### 1. Shannon Entropy
The theoretical zero-order empirical entropy \(H(X)\) represents the absolute minimum average number of bits required to represent a symbol without loss of information:
\[
H(X) = -\sum_{x \in \mathcal{X}} p(x) \log_2 p(x) \quad \text{[bits/symbol]}
\]
- For a byte alphabet (\(|\mathcal{X}| = 256\)), the maximum possible entropy is \(\log_2(256) = 8.0\) bits/symbol (achieved by a uniform distribution).
- **Shannon Source Coding Lower Bound**:
  \[
  \text{Min Lossless Size (Bytes)} = \frac{N \times H(X)}{8}
  \]

### 2. Coding Efficiency and Redundancy
- **Average Code Length**: \(L_{\text{avg}} = \sum p(x) \ell(x)\) bits/symbol
- **Coding Efficiency**: \(\eta = \frac{H(X)}{L_{\text{avg}}}\)
- **Redundancy**: \(R = 1 - \eta\)

### 3. Conditional Entropy & Higher-Order Statistics
Zero-order entropy assumes symbols are independent and identically distributed (i.i.d.). Real-world data exhibits strong sequential dependencies, measured by conditional entropy:
\[
H(X_i \mid X_{i-1}) = -\sum_{x, y} p(x, y) \log_2 \frac{p(x, y)}{p(x)}
\]
When \(H(X_i \mid X_{i-1}) \ll H(X)\), block-level Huffman (e.g., block size 2), dictionary methods (LZW), or Delta differencing drastically outperform zero-order models.

---

## 🛠 Implemented Algorithms (From Scratch)

### 1. Huffman Encoding (`algorithms/huffman.py`)
- **Deterministic Priority Queue**: Implements min-heap tree construction with deterministic tie-breaking based on symbol byte values.
- **Configurable Symbol Blocks**: Supports byte-level (\(K=1\)) and multi-byte blocks (\(K=2, 3, 4\)) with exact handling of incomplete final blocks.
- **Compact Tree Serialization**: Pre-order bitstream serialization where internal nodes are marked by bit `1` and leaves by bit `0` followed by symbol bytes.
- **Visualizer**: ASCII tree renderer displaying branches, weights, and prefix codes.

### 2. Integer Arithmetic Coding (`algorithms/arithmetic.py`)
- **Numerically Safe 32-bit Integer Arithmetic**: Implements Witten-Neal-Cleary (WNC) arithmetic coding using integer bounds rather than floating-point math.
- **Underflow Handling (E3 Mapping)**: Tracks pending bits when intervals straddle the midpoint (\(low \ge 1/4\) and \(high < 3/4\)).
- **Static & Adaptive Models**:
  - *Static*: Precomputes source frequencies and serializes the frequency table in the container metadata.
  - *Adaptive*: Incrementally updates cumulative frequency distributions symbol-by-symbol with dynamic count rescaling to prevent integer overflow.
- **Visualizer**: Step-by-step interval subdivision and hexadecimal bound narrowing.

### 3. Shannon-Fano Encoding (`algorithms/shannon_fano.py`)
- **Recursive Binary Partitioning**: Divides frequency-sorted symbol subsets to minimize absolute frequency divergence \(|S_1 - S_2|\).
- **Deterministic Tie-Breaking**: Secondary sorting on byte values ensures encoder and decoder agree on every partition.
- **Prefix Trie Reconstruction**: Bit-level trie decoding from serialized codebooks.

### 4. Run-Length Encoding (RLE) (`algorithms/rle.py`)
- **Binary-Safe PackBits Scheme**: Control byte \(n \in [0, 127]\) indicates \(n+1\) literal bytes; \(n \in [129, 255]\) indicates \(257 - n\) repetitions of the following byte.
- Handles arbitrary binary streams without expansion vulnerabilities.

### 5. Lempel-Ziv-Welch (LZW) (`algorithms/lzw.py`)
- **Dictionary Compression**: Online dictionary building from single-byte alphabet up to 65,535 entries.
- **KwKwK Edge Case**: Fully solves the classic decompressor dilemma where a codeword is not yet present in the decoder dictionary.

### 6. Delta Preprocessing (`algorithms/delta.py`)
- **Reversible Byte Differencing**: Computes \(y[0] = x[0], y[i] = (x[i] - x[i-1]) \pmod{256}\).
- Invertible via running prefix sums; turns smooth or continuous data into near-zero distributions before Huffman coding.

---

## 📦 Container Binary Specification (`.clab`)

Every compressed file produced by the laboratory is completely self-contained and independently decompressible:

| Field | Type | Description |
|---|---|---|
| `MAGIC` | 4 bytes ASCII | Fixed identifier: `CLAB` |
| `VERSION` | 1 byte (uint8) | Format version (`1`) |
| `ALGORITHM_ID` | 1 byte (uint8) | 1=Huffman, 2=Arith-Static, 3=Arith-Adaptive, 4=Shannon-Fano, 5=LZW, 6=RLE, 7=Delta-Huffman |
| `FLAGS` | 2 bytes (uint16 BE) | Bit 0: IsArchive (Folder), Bit 1: DeltaApplied |
| `BLOCK_SIZE` | 1 byte (uint8) | Symbol block size (1..16) |
| `ORIGINAL_SIZE`| 8 bytes (uint64 BE) | Exact uncompressed payload byte size |
| `CRC32` | 4 bytes (uint32 BE) | Uncompressed data CRC32 checksum |
| `FILENAME_LEN` | 2 bytes (uint16 BE) | Length \(N\) of original filename |
| `FILENAME` | \(N\) bytes UTF-8 | Preserved filename |
| `MODEL_LEN` | 4 bytes (uint32 BE) | Length of serialized tree/model/codebook |
| `MODEL_METADATA`| Variable | Serialized decoding structures |
| `PAYLOAD_LEN` | 8 bytes (uint64 BE) | Length of compressed bitstream payload |
| `PAYLOAD` | Variable | Encoded bitstream / byte stream |

### Directory & Folder Archiving
When compressing a directory, the engine recursively archives directory hierarchy, subdirectories, empty folders, and file streams into a safe binary archive with path-traversal protection.

---

## 🎲 Controlled Random File Generator

The laboratory includes a generator with mathematically defined modes:
1. **Uniform Random**: Theoretical entropy = \(8.0\) bits.
2. **Biased (Zipfian)**: Probability \(p(i) \propto 1 / (i+1)^s\), where skew parameter \(s \ge 0\) controls bias.
3. **Repeated Patterns**: Pattern repetition with controlled substitution noise rate.
4. **Periodic Waveforms**: Sinusoidal and sawtooth waveforms discretized to bytes.
5. **Controlled Entropy**: Uses bisection search on Gibbs distribution temperature \(\beta\) to match an exact target entropy \(H_0 \in [0.1, 8.0]\) bits.
6. **Markov Chain**: 1st-order Markov sequence with persistence parameter \(\alpha \in [0.0, 0.99]\) simulating strong temporal correlation.

---

## 🏆 Compression Tournament System

The tournament engine benchmarks multiple algorithms against identical input data, recording:
- Original size vs. Total container size (including all metadata and headers).
- Compression ratio & space saving percentage.
- Compression time (ms) & Decompression time (ms).
- Measured source entropy & theoretical Shannon lower bound.
- **Strict Invariant Verification**: Automatically verifies \(\text{decompress}(\text{compress}(\text{data})) \equiv \text{data}\).
- Export to **CSV** and **JSON**.

---

## 🚀 Execution Instructions

### Prerequisites
Install the required supporting libraries:
```bash
pip install -r requirements.txt
```

### Launch Graphical Desktop Application (GUI)
```bash
python main.py
```

### Run Command-Line Tournament Demo (Headless)
```bash
python main.py --cli
```

### Run Test Suite
```bash
pytest tests -v
```
All 39 unit and integration tests verify bitstreams, edge cases, corruption detection, folder archiving, and exact lossless roundtrips across all algorithms.
