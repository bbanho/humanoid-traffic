"""
Analise espectral de padroes de tráfego.
Transforma series temporais de requests em dominio de frequencia
para detectar padrões periodicos (bot) vs ruido 1/f (humano).
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
    flatness: float  # spectral flatness (Wiener entropy)
    slope: float  # inclinacao do espectro (1/f^a)


class SpectralAnalyzer:
    """
    Analisador espectral de tráfego.
    
    Humanos: espectro com ruido 1/f (pink noise), alta entropia, sem picos
    Bots: espectro com picos dominantes (periodicidade), baixa entropia
    """
    
    def __init__(self, sampling_rate: float = 1.0, nfft: int = 256):
        """
        Args:
            sampling_rate: taxa de amostragem (1 = 1 request por unidade)
            nfft: tamanho da FFT (zero-padding para interpolacao)
        """
        self.sampling_rate = sampling_rate
        self.nfft = nfft
    
    def _build_signal(self, intervals: List[float]) -> np.ndarray:
        """
        Constroi sinal temporal a partir de intervalos entre requests.
        
        O sinal e a serie de intervalos (delta_t) ao longo do tempo.
        """
        signal = np.array(intervals, dtype=float)
        
        # Remove tendencia (detrend)
        signal = signal - np.mean(signal)
        
        # Zero-padding
        if len(signal) < self.nfft:
            signal = np.pad(signal, (0, self.nfft - len(signal)))
        
        return signal
    
    def _fft(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """FFT retorna frequencias e magnitudes."""
        fft_result = np.fft.rfft(signal, n=self.nfft)
        frequencies = np.fft.rfftfreq(self.nfft, d=1.0/self.sampling_rate)
        magnitudes = np.abs(fft_result)
        return frequencies, magnitudes
    
    def _dominant_frequency(self, frequencies: np.ndarray, magnitudes: np.ndarray) -> Tuple[float, float]:
        """Frequencia dominante (exclui DC)."""
        if len(magnitudes) <= 1:
            return 0.0, 0.0
        # Exclui DC (indice 0)
        idx = np.argmax(magnitudes[1:]) + 1
        return frequencies[idx], magnitudes[idx]
    
    def _spectral_entropy(self, magnitudes: np.ndarray) -> float:
        """
        Entropia espectral.
        
        Alta = espectro plano (ruido) = humano
        Baixa = espectro concentrado (periodico) = bot
        """
        # Normaliza
        total = np.sum(magnitudes[1:])  # exclui DC
        if total == 0:
            return 0.0
        probs = magnitudes[1:] / total
        
        # Entropia de Shannon
        probs = probs[probs > 0]
        entropy = -np.sum(probs * np.log2(probs))
        
        # Normaliza por max entropy
        max_entropy = np.log2(len(probs))
        if max_entropy == 0:
            return 0.0
        return float(entropy / max_entropy)
    
    def _spectral_flatness(self, magnitudes: np.ndarray) -> float:
        """
        Flatness espectral (Wiener entropy).
        
        1.0 = ruido branco (flat)
        0.0 = puro tom (periodico)
        """
        mags = magnitudes[1:]  # exclui DC
        if len(mags) == 0 or np.any(mags <= 0):
            return 0.0
        
        geometric_mean = np.exp(np.mean(np.log(mags)))
        arithmetic_mean = np.mean(mags)
        
        if arithmetic_mean == 0:
            return 0.0
        return float(geometric_mean / arithmetic_mean)
    
    def _spectral_slope(self, frequencies: np.ndarray, magnitudes: np.ndarray) -> float:
        """
        Inclinacao do espectro (lei de potencia 1/f^a).
        
        Ruido 1/f (pink noise): a ≈ 1.0 (humano)
        Ruido branco: a ≈ 0.0
        Ruido 1/f^2 (brown noise): a ≈ 2.0
        """
        freqs = frequencies[1:]
        mags = magnitudes[1:]
        
        if len(freqs) < 2 or np.any(freqs <= 0) or np.any(mags <= 0):
            return 0.0
        
        log_freqs = np.log10(freqs)
        log_mags = np.log10(mags)
        
        slope, _ = np.polyfit(log_freqs, log_mags, 1)
        return float(slope)
    
    def analyze(self, intervals: List[float]) -> SpectralSignature:
        """
        Analisa serie temporal de intervalos.
        
        Args:
            intervals: lista de delta_t entre requests (segundos)
        
        Returns:
            SpectralSignature com metricas
        """
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
        """
        Classifica padrão como HUMANO ou BOT baseado no espectro.
        
        Criterios:
        - Entropia espectral > 0.7 → humano (espectro disperso)
        - Flatness > 0.3 → humano (ruido)
        - Slope entre -2.0 e -0.5 → humano (1/f-like)
        - Dominant magnitude < 30% do total → humano (sem pico)
        """
        sig = self.analyze(intervals)
        
        # Score de humanidade (0-1)
        scores = {
            "entropy": min(1.0, sig.spectral_entropy / 0.7),
            "flatness": min(1.0, sig.flatness / 0.3),
            "slope": 1.0 if -2.0 < sig.slope < -0.5 else 0.0,
        }
        
        # Magnitude dominante relativa
        total_mag = np.sum(sig.magnitudes[1:])
        dom_ratio = sig.dominant_magnitude / total_mag if total_mag > 0 else 1.0
        scores["no_dominant"] = 1.0 if dom_ratio < 0.3 else 0.0
        
        # Media ponderada
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
    Gera intervalos com ruido 1/f (pink noise) — caracteristico de comportamento humano.
    
    Usando Voss-McCartney algorithm para gerar 1/f noise.
    """
    rng = np.random.RandomState(seed)
    
    # Soma de fontes de ruido com diferentes taxas de atualizacao
    sources = np.zeros(n)
    for k in range(1, int(np.log2(n)) + 1):
        # Cada fonte atualiza a cada 2^k passos
        step = 2 ** k
        updates = rng.randn(n // step + 1)
        # Interpola
        interpolated = np.repeat(updates, step)[:n]
        sources += interpolated / (k ** 0.5)  # amplitude ~ 1/sqrt(k)
    
    # Normaliza para intervalos de 20-60 segundos
    sources = (sources - np.mean(sources)) / np.std(sources)
    intervals = 30 + sources * 10  # media=30, std=10
    intervals = np.clip(intervals, 1, 120)
    
    return intervals.tolist()


def generate_bot_intervals(n: int, interval: float = 5.0, jitter: float = 0.1) -> List[float]:
    """Gera intervalos fixos (bot) com pequeno jitter."""
    rng = np.random.RandomState(42)
    return (interval + rng.randn(n) * jitter).tolist()


def generate_mixed_intervals(n: int, seed: int = 42) -> List[float]:
    """Gera intervalos com multiplas frequencias sobrepostas (humano real)."""
    rng = np.random.RandomState(seed)
    
    t = np.arange(n)
    
    # Multiplas componentes de frequencia
    # - Ciclo de trabalho (periodo ~60 requests = ~30 min)
    # - Pausas (periodo ~200 requests = ~100 min)
    # - Variacao rapida (ruido)
    signal = (
        10 * np.sin(2 * np.pi * t / 60) +
        20 * np.sin(2 * np.pi * t / 200 + 1.5) +
        5 * rng.randn(n)
    )
    
    # Base de 30 segundos
    intervals = 30 + signal
    intervals = np.clip(intervals, 1, 120)
    
    return intervals.tolist()
