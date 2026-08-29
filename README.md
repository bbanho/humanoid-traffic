# Humanoid Traffic

> Repo para formalização da análise espectral de detecção de automação em APIs de IA.

## Estrutura

```
humanoid-traffic/
├── README.md                    # Visão geral
├── docs/
│   └── roteiro_abntex.tex       # Roteiro formal (ABNT NBR 14724:2011)
├── src/
│   └── spectral.py              # Analisador espectral (FFT + entropia)
├── scripts/
│   └── demo_spectral.py         # Demonstração
└── tests/
```

## O Modelo Espectral

Em vez de features pontuais, analisamos o **espectro de frequência** dos intervalos entre requests:

$$X(f) = \int_{-\infty}^{\infty} x(t) \cdot e^{-i2\pi ft} dt$$

**Hipótese central:**
- Humanos geram **ruído 1/f** (pink noise): espectro disperso, alta entropia, sem picos
- Bots geram **padrões periódicos**: picos espectrais dominantes, baixa entropia

## Métricas

| Métrica | Humano | Bot | Limiar |
|---------|--------|-----|--------|
| Entropia espectral | > 0.7 | < 0.4 | 0.5 |
| Spectral flatness | > 0.3 | < 0.1 | 0.2 |
| Inclinação (α) | ~ -1.0 | > -0.5 | -0.7 |
| Freq. dominante | < 30% do total | > 50% | 40% |

## Uso

```python
from spectral import SpectralAnalyzer

analyzer = SpectralAnalyzer(nfft=256)
result = analyzer.classify(intervals_list)

print(result["status"])       # "HUMANO" ou "BOT"
print(result["human_score"])  # 0-1
```

## Próximos Passos

1. Capturar tráfego real com gateway CA (1 semana)
2. Calcular assinaturas espectrais por perfil de usuário
3. Validar hipóteses com A/B testing entre chaves
4. Construir modelo preditivo de probabilidade de ban
5. Síntese de tráfego com espectro compatível (1/f)

## Referências

- Shannon, C. E. (1948). A mathematical theory of communication.
- Voss, R. F. & Clarke, J. (1978). 1/f noise in music.
- NBR 14724:2011 — Trabalhos acadêmicos — Apresentação.
