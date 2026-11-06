"""
Análise espectral de padrões de tráfego.
Transforma series temporais de requests em domínio de frequência
para detectar padrões periódicos (bot) vs ruído 1/f (humano).
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class SpectralSignature:
    """Assinatura espectral de um padrão de tráfego."""
    frequencies: np.ndarray
    magnitudes: np.ndarray
    dominant_freq: float
    dominant_magnitude: float
    spectral_entropy: float
    flatness: float
    slope: float


class SpectralAnalyzer:
    """
    Analisador espectral de tráfego.

    Humanos: espectro com ruído 1/f (pink noise), alta entropia, sem picos
    Bots: espectro com picos dominantes (periodicidade), baixa entropia
    """

    def __init__(self, sampling_rate: float = 1.0, nfft: int = 256):
        self.sampling_rate = sampling_rate
        self.nfft = nfft

    def _build_signal(self, intervals: List[float]) -> np.ndarray:
        signal = np.array(intervals, dtype=float)
        signal = signal - np.mean(signal)
        if len(signal) < self.nfft:
            signal = np.pad(signal, (0, self.nfft - len(signal)))
        return signal

    def _fft(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        fft_result = np.fft.rfft(signal, n=self.nfft)
        frequencies = np.fft.rfftfreq(self.nfft, d=1.0/self.sampling_rate)
        magnitudes = np.abs(fft_result)
        return frequencies, magnitudes

    def _dominant_frequency(self, frequencies: np.ndarray, magnitudes: np.ndarray) -> Tuple[float, float]:
        if len(magnitudes) <= 1:
            return 0.0, 0.0
        idx = np.argmax(magnitudes[1:]) + 1
        return float(frequencies[idx]), float(magnitudes[idx])

    def _spectral_entropy(self, magnitudes: np.ndarray) -> float:
        mags = magnitudes[1:]
        total = np.sum(mags)
        if total == 0:
            return 0.0
        probs = mags / total
        probs = probs[probs > 0]
        if len(probs) == 0:
            return 0.0
        entropy = -np.sum(probs * np.log2(probs))
        max_entropy = np.log2(len(probs))
        if max_entropy == 0:
            return 0.0
        return float(entropy / max_entropy)

    def _spectral_flatness(self, magnitudes: np.ndarray) -> float:
        mags = magnitudes[1:]
        if len(mags) == 0:
            return 0.0

        mags = mags[mags > 0]
        if len(mags) == 0:
            return 0.0

        geometric_mean = np.exp(np.mean(np.log(mags)))
        arithmetic_mean = np.mean(mags)

        if arithmetic_mean == 0:
            return 0.0
        return float(geometric_mean / arithmetic_mean)

    def _spectral_slope(self, frequencies: np.ndarray, magnitudes: np.ndarray) -> float:
        freqs = frequencies[1:]
        mags = magnitudes[1:]

        if len(freqs) < 2:
            return 0.0

        valid = mags > 0
        freqs = freqs[valid]
        mags = mags[valid]
        if len(freqs) < 2:
            return 0.0

        log_freqs = np.log10(freqs)
        log_mags = np.log10(mags)

        slope, _ = np.polyfit(log_freqs, log_mags, 1)
        return float(slope)

    def analyze(self, intervals: List[float]) -> SpectralSignature:
        signal = self._build_signal(intervals)
        frequencies, magnitudes = self._fft(signal)
        dom_freq, dom_mag = self._dominant_frequency(frequencies, magnitudes)
        return SpectralSignature(
            frequencies=frequencies,
            magnitudes=magnitudes,
            dominant_freq=dom_freq,
            dominant_magnitude=dom_mag,
            spectral_entropy=self._spectral_entropy(magnitudes),
            flatness=self._spectral_flatness(magnitudes),
            slope=self._spectral_slope(frequencies, magnitudes),
        )

    def classify(self, intervals: List[float]) -> dict:
        sig = self.analyze(intervals)

        scores = {
            "entropy": min(1.0, sig.spectral_entropy / 0.7),
            "flatness": min(1.0, sig.flatness / 0.3),
            "slope": 1.0 if -2.0 < sig.slope < -0.5 else 0.0,
        }

        total_mag = np.sum(sig.magnitudes[1:])
        dom_ratio = sig.dominant_magnitude / total_mag if total_mag > 0 else 1.0
        scores["no_dominant"] = 1.0 if dom_ratio < 0.3 else 0.0

        weights = {"entropy": 0.35, "flatness": 0.25, "slope": 0.20, "no_dominant": 0.20}
        human_score = sum(scores[k] * weights[k] for k in scores)

        return {
            "human_score": round(human_score, 3),
            "status": "HUMANO" if human_score > 0.6 else "BOT",
            "metrics": {
                "spectral_entropy": round(sig.spectral_entropy, 3),
                "spectral_flatness": round(sig.flatness, 3),
                "spectral_slope": round(sig.slope, 3),
                "dominant_freq": round(sig.dominant_freq, 4),
                "dominant_ratio": round(dom_ratio, 3),
            },
            "scores": {k: round(v, 3) for k, v in scores.items()},
        }


def generate_human_intervals(n: int, seed: int = 42) -> List[float]:
    """
    Gera intervalos com ruído 1/f (pink noise) — característico de comportamento humano.

    Usa o algoritmo Voss-McCartney modificado para gerar 1/f noise.
    """
    rng = np.random.RandomState(seed)

    sources = np.zeros(n)
    for k in range(1, int(np.log2(n)) + 1):
        step = 2 ** k
        updates = rng.randn(n // step + 1)
        interpolated = np.repeat(updates, step)[:n]
        sources += interpolated / (k ** 0.5)

    sources = (sources - np.mean(sources)) / np.std(sources)
    intervals = 30 + sources * 10
    intervals = np.clip(intervals, 1, 120)

    return intervals.tolist()


def generate_bot_intervals(n: int, interval: float = 5.0, jitter: float = 0.1) -> List[float]:
    """Gera intervalos fixos (bot) com pequeno jitter."""
    rng = np.random.RandomState(42)
    return (interval + rng.randn(n) * jitter).tolist()


def generate_mixed_intervals(n: int, seed: int = 42) -> List[float]:
    """Gera intervalos com múltiplas frequências sobrepostas (humano real)."""
    rng = np.random.RandomState(seed)

    t = np.arange(n)

    signal = (
        10 * np.sin(2 * np.pi * t / 60) +
        20 * np.sin(2 * np.pi * t / 200 + 1.5) +
        5 * rng.randn(n)
    )

    intervals = 30 + signal
    intervals = np.clip(intervals, 1, 120)

    return intervals.tolist()