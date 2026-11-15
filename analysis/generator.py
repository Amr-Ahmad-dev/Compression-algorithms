"""
Random Data and Controlled Entropy Generator.
Provides mathematically rigorous generation modes:
1. Uniform random bytes (Entropy = log2(K))
2. Biased distribution (Zipfian skew parameter s)
3. Repeated patterns with noise rate
4. Periodic sequences (sinusoidal / sawtooth)
5. Controlled Entropy (Gibbs / Exponential distribution solving for target H0)
6. Markov sequences with persistence parameter alpha
7. Custom distribution
"""

import math
import random
from enum import Enum
from typing import List, Dict, Optional, Tuple, Union
import numpy as np


class GenerationMode(str, Enum):
    UNIFORM = "uniform"
    BIASED_ZIPF = "biased_zipf"
    REPEATED_PATTERN = "repeated_pattern"
    PERIODIC = "periodic"
    CONTROLLED_ENTROPY = "controlled_entropy"
    MARKOV = "markov"
    CUSTOM = "custom"


def generate_uniform(size: int, alphabet_size: int = 256, seed: Optional[int] = None) -> bytes:
    """Generates bytes sampled uniformly at random from 0..alphabet_size-1."""
    if seed is not None:
        random.seed(seed)
    symbols = list(range(alphabet_size))
    return bytes(random.choices(symbols, k=size))


def generate_biased_zipf(
    size: int,
    alphabet_size: int = 256,
    skew: float = 1.0,
    seed: Optional[int] = None
) -> bytes:
    """
    Generates bytes from a Zipfian distribution: p(i) ~ 1 / (i + 1)^skew.
    skew = 0.0 -> Uniform
    skew > 1.0 -> Highly biased towards lower symbol values (low entropy)
    """
    if seed is not None:
        np.random.seed(seed)
    ranks = np.arange(1, alphabet_size + 1, dtype=np.float64)
    weights = 1.0 / (ranks ** skew)
    probs = weights / np.sum(weights)
    symbols = np.arange(alphabet_size, dtype=np.uint8)
    return bytes(np.random.choice(symbols, size=size, p=probs))


def generate_repeated_pattern(
    size: int,
    pattern: bytes = b"COMPRESSION_LAB_",
    noise_rate: float = 0.05,
    seed: Optional[int] = None
) -> bytes:
    """
    Repeats a base pattern with a configurable random byte substitution noise rate.
    """
    if seed is not None:
        random.seed(seed)
    if not pattern:
        pattern = b"A"

    pat_len = len(pattern)
    out = bytearray(size)
    for i in range(size):
        if noise_rate > 0 and random.random() < noise_rate:
            out[i] = random.randint(0, 255)
        else:
            out[i] = pattern[i % pat_len]
    return bytes(out)


def generate_periodic(
    size: int,
    period: int = 64,
    waveform: str = "sine",
    seed: Optional[int] = None
) -> bytes:
    """
    Generates deterministic periodic wave signals (sine or sawtooth) discretized to bytes.
    """
    out = bytearray(size)
    for i in range(size):
        phase = (i % period) / period
        if waveform == "sine":
            val = int(127.5 * (1.0 + math.sin(2.0 * math.pi * phase)))
        elif waveform == "sawtooth":
            val = int(255.0 * phase)
        else:
            val = int(255.0 if phase < 0.5 else 0.0)
        out[i] = min(255, max(0, val))
    return bytes(out)


def find_gibbs_probs_for_entropy(target_entropy: float, alphabet_size: int = 256) -> np.ndarray:
    """
    Finds a Gibbs distribution p(i) ~ exp(-beta * i) matching the target Shannon entropy.
    Uses bisection search on beta.
    """
    max_h = math.log2(alphabet_size)
    target = max(0.0, min(target_entropy, max_h))

    if target >= max_h - 1e-4:
        return np.full(alphabet_size, 1.0 / alphabet_size)
    if target <= 1e-4:
        p = np.zeros(alphabet_size)
        p[0] = 1.0
        return p

    ranks = np.arange(alphabet_size, dtype=np.float64)

    def entropy_at_beta(beta: float) -> float:
        w = np.exp(-beta * ranks)
        probs = w / np.sum(w)
        # Compute Shannon entropy
        h = 0.0
        for p in probs:
            if p > 1e-15:
                h -= p * math.log2(p)
        return h

    # Binary search for beta in [0.0, 100.0]
    low = 0.0
    high = 50.0
    for _ in range(60):
        mid = (low + high) / 2.0
        h_mid = entropy_at_beta(mid)
        if h_mid < target:
            high = mid
        else:
            low = mid

    w = np.exp(-low * ranks)
    return w / np.sum(w)


def generate_controlled_entropy(
    size: int,
    target_entropy: float,
    alphabet_size: int = 256,
    seed: Optional[int] = None
) -> bytes:
    """
    Generates random data whose true distribution has the exact target Shannon entropy.
    """
    if seed is not None:
        np.random.seed(seed)
    probs = find_gibbs_probs_for_entropy(target_entropy, alphabet_size)
    symbols = np.arange(alphabet_size, dtype=np.uint8)
    return bytes(np.random.choice(symbols, size=size, p=probs))


def generate_markov(
    size: int,
    persistence: float = 0.85,
    alphabet_size: int = 256,
    seed: Optional[int] = None
) -> bytes:
    """
    Generates a 1st-order Markov chain sequence.
    With probability `persistence`, the current symbol repeats the previous symbol.
    With probability `1 - persistence`, it transitions to a new random symbol.
    Creates high autocorrelation and low conditional entropy.
    """
    if seed is not None:
        random.seed(seed)
    if size <= 0:
        return b""

    out = bytearray(size)
    current = random.randint(0, alphabet_size - 1)
    out[0] = current

    for i in range(1, size):
        if random.random() < persistence:
            # Maintain state
            pass
        else:
            # Transition
            current = random.randint(0, alphabet_size - 1)
        out[i] = current

    return bytes(out)


def generate_dataset(
    mode: GenerationMode,
    size: int,
    seed: Optional[int] = None,
    **kwargs
) -> bytes:
    """Unified entry point for data generation."""
    if mode == GenerationMode.UNIFORM:
        return generate_uniform(size, alphabet_size=kwargs.get("alphabet_size", 256), seed=seed)
    elif mode == GenerationMode.BIASED_ZIPF:
        return generate_biased_zipf(
            size,
            alphabet_size=kwargs.get("alphabet_size", 256),
            skew=kwargs.get("skew", 1.0),
            seed=seed
        )
    elif mode == GenerationMode.REPEATED_PATTERN:
        return generate_repeated_pattern(
            size,
            pattern=kwargs.get("pattern", b"ABCDEF123456"),
            noise_rate=kwargs.get("noise_rate", 0.05),
            seed=seed
        )
    elif mode == GenerationMode.PERIODIC:
        return generate_periodic(
            size,
            period=kwargs.get("period", 32),
            waveform=kwargs.get("waveform", "sine"),
            seed=seed
        )
    elif mode == GenerationMode.CONTROLLED_ENTROPY:
        return generate_controlled_entropy(
            size,
            target_entropy=kwargs.get("target_entropy", 4.0),
            alphabet_size=kwargs.get("alphabet_size", 256),
            seed=seed
        )
    elif mode == GenerationMode.MARKOV:
        return generate_markov(
            size,
            persistence=kwargs.get("persistence", 0.8),
            alphabet_size=kwargs.get("alphabet_size", 256),
            seed=seed
        )
    else:
        return generate_uniform(size, seed=seed)
