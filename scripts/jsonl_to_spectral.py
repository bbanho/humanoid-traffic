#!/usr/bin/env python3
"""
JSONL → Spectral Features Pipeline
Converte logs do gateway_ca.py em features espectrais para análise.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from spectral import SpectralAnalyzer, generate_human_intervals, generate_bot_intervals, generate_mixed_intervals


def load_jsonl(filepath: Path) -> list:
    """Carrega arquivo JSONL."""
    records = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def group_by_session(records: list, max_gap_seconds: float = 300) -> list:
    """
    Agrupa requests em sessões baseadas em gap temporal.
    
    Args:
        records: lista de records ordenados por timestamp
        max_gap_seconds: gap máximo para considerar mesma sessão (default 5 min)
    
    Returns:
        Lista de sessões, cada uma com lista de records
    """
    if not records:
        return []
    
    # Ordena por timestamp
    records = sorted(records, key=lambda r: r.get('timestamp_start', ''))
    
    sessions = []
    current_session = [records[0]]
    
    for i in range(1, len(records)):
        prev = records[i-1]
        curr = records[i]
        
        try:
            prev_time = datetime.fromisoformat(prev['timestamp_start'].replace('Z', '+00:00'))
            curr_time = datetime.fromisoformat(curr['timestamp_start'].replace('Z', '+00:00'))
            gap = (curr_time - prev_time).total_seconds()
        except (KeyError, ValueError):
            gap = float('inf')
        
        if gap <= max_gap_seconds:
            current_session.append(curr)
        else:
            sessions.append(current_session)
            current_session = [curr]
    
    if current_session:
        sessions.append(current_session)
    
    return sessions


def extract_intervals(session: list) -> list:
    """Extrai array de intervalos (delta_t) de uma sessão."""
    intervals = []
    for i in range(1, len(session)):
        try:
            prev_time = datetime.fromisoformat(session[i-1]['timestamp_start'].replace('Z', '+00:00'))
            curr_time = datetime.fromisoformat(session[i]['timestamp_start'].replace('Z', '+00:00'))
            gap = (curr_time - prev_time).total_seconds()
            if gap > 0:
                intervals.append(gap)
        except (KeyError, ValueError):
            continue
    return intervals


def extract_tokens(session: list) -> list:
    """Extrai array de token counts de uma sessão."""
    tokens = []
    for record in session:
        tc = record.get('response_total_tokens') or record.get('request_token_count')
        if tc is not None:
            tokens.append(tc)
    return tokens


def extract_errors(session: list) -> list:
    """Extrai error types de uma sessão."""
    errors = []
    for record in session:
        et = record.get('error_type')
        if et:
            errors.append(et)
    return errors


def process_log_file(log_dir: Path, output_dir: Path):
    """Processa todos os logs JSONL em um diretório."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    log_files = list(log_dir.glob("*.jsonl"))
    if not log_files:
        print(f"Nenhum arquivo .jsonl encontrado em {log_dir}")
        return
    
    all_sessions = []
    
    for log_file in log_files:
        print(f"Processando {log_file.name}...")
        records = load_jsonl(log_file)
        sessions = group_by_session(records)
        print(f"  {len(sessions)} sessões encontradas")
        all_sessions.extend(sessions)
    
    print(f"Total: {len(all_sessions)} sessões")
    
    # Analisador espectral (referência: developer profile)
    ref_interval = 30.0  # segundos
    analyzer = SpectralAnalyzer()
    # Note: SpectralAnalyzer não precisa de referência pré-definida para analyze()
    
    # Processa cada sessão
    spectral_results = []
    
    for i, session in enumerate(all_sessions):
        intervals = extract_intervals(session)
        tokens = extract_tokens(session)
        errors = extract_errors(session)
        providers = [r.get('provider', 'unknown') for r in session]
        
        if len(intervals) < 2:
            continue  # Sessão muito curta
        
        # Análise espectral
        spectral = analyzer.analyze(intervals)
        
        # Features agregadas
        result = {
            "session_id": i,
            "num_requests": len(session),
            "duration_seconds": sum(intervals),
            "avg_interval": np.mean(intervals),
            "std_interval": np.std(intervals),
            "cv_interval": np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 0,
            "total_tokens": sum(tokens) if tokens else 0,
            "avg_tokens": np.mean(tokens) if tokens else 0,
            "error_count": len(errors),
            "error_rate": len(errors) / len(session) if session else 0,
            "dominant_provider": max(set(providers), key=providers.count) if providers else "unknown",
            
            # Features espectrais
            "spectral_entropy": spectral.spectral_entropy,
            "spectral_flatness": spectral.flatness,
            "spectral_slope": spectral.slope,
            "dominant_freq": spectral.dominant_freq,
            "dominant_magnitude": spectral.dominant_magnitude,
            
            # Classificação
            "human_score": 0.0,  # Será calculado abaixo
        }
        
        # Calcula human_score (heurística)
        score = 0.0
        if spectral.spectral_entropy > 0.7:
            score += 0.35
        if spectral.flatness > 0.3:
            score += 0.25
        if -2.0 < spectral.slope < -0.5:
            score += 0.20
        dom_ratio = spectral.dominant_magnitude / (sum([1 for _ in intervals]) + 1)
        if dom_ratio < 0.3:
            score += 0.20
        result["human_score"] = round(score, 3)
        result["status"] = "HUMANO" if score > 0.6 else "BOT"
        
        spectral_results.append(result)
        
        if i % 50 == 0:
            print(f"  Processadas {i+1}/{len(all_sessions)} sessões")
    
    # Salva resultados
    output_file = output_dir / f"spectral_features_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(spectral_results, f, indent=2, default=str)
    
    print(f"\nResultados salvos em: {output_file}")
    print(f"Sessões analisadas: {len(spectral_results)}")
    
    # Resumo
    humanos = sum(1 for r in spectral_results if r['status'] == 'HUMANO')
    bots = len(spectral_results) - humanos
    print(f"HUMANO: {humanos}, BOT: {bots}")
    
    return spectral_results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="JSONL → Spectral Features")
    parser.add_argument("--log-dir", type=str, default="./logs", help="Diretório com logs JSONL")
    parser.add_argument("--output-dir", type=str, default="./spectral_output", help="Diretório de saída")
    
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir)
    output_dir = Path(args.output_dir)
    
    if not log_dir.exists():
        print(f"Diretório não encontrado: {log_dir}")
        return 1
    
    process_log_file(log_dir, output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())