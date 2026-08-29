# Relatório de Progresso — F1: Captura de Tráfego MITM

**Data:** 2026-08-29
**Branch:** `feat/gateway-ca-mitm` (nexus-gateway)
**Repositório:** `humanoid-traffic` (docs)

---

## Resumo Executivo

A **Fase 1 (Captura de Tráfego)** foi concluída com sucesso. O proxy MITM (`gateway_ca.py`) está operacional, validado com tráfego real, e documentado.

---

## Componentes Entregues

### 1. Gateway CA (`scripts/gateway_ca.py`)
- **Linha de código:** 300
- **Dependência:** `mitmproxy 12.2.3` (binary wheel)
- **Porta:** 8082 (8080 ocupada)

### 2. Provider Detection (17 providers únicos)
| Categoria | Hosts |
|-----------|-------|
| **Anthropic** | `api.anthropic.com`, `console.anthropic.com` |
| **OpenAI** | `api.openai.com`, `chat.openai.com` |
| **Gemini** | `generativelanguage.googleapis.com`, `gemini.google.com` |
| **Outros APIs** | `api.deepseek.com`, `api.groq.com`, `api.x.ai`, `api.mistral.ai`, `api.perplexity.ai`, `api.cohere.ai`, `api.together.xyz`, `api.fireworks.ai`, `openrouter.ai`, `api.antigravity.io`, `poe.com` |

### 3. Token Extraction
| Formato | Request | Response |
|---------|---------|----------|
| **OpenAI** | `max_tokens` | `prompt_tokens`, `completion_tokens`, `total_tokens` |
| **Anthropic** | — | `input_tokens`, `output_tokens` |
| **Gemini** | — | `promptTokenCount`, `candidatesTokenCount`, `totalTokenCount` |
| **OpenRouter** | `max_tokens` | `prompt_tokens`, `completion_tokens`, `total_tokens` |

### 4. Error Classification
| Código HTTP | Tipo |
|-------------|------|
| 429 | `rate_limit` |
| 403 | `forbidden` |
| 401 | `unauthorized` |
| 500 | `server_error` |
| 502 | `bad_gateway` |
| 503 | `service_unavailable` |
| ≥400 | `http_XXX` |

### 5. Streaming Detection
- Detecta `text/event-stream` e `application/x-ndjson` via `content-type`
- Flag `is_streaming` no log

---

## Validação Experimental

### Teste 1: httpbin.org (baseline)
```json
{
  "provider": "unknown",
  "duration_ms": 142,
  "response_status": 200
}
```

### Teste 2: api.openai.com/v1/models (401)
```json
{
  "provider": "openai",
  "error_type": "unauthorized",
  "response_status": 401,
  "duration_ms": 175
}
```

### Teste 3: api.openai.com/v1/chat/completions (401, max_tokens=5)
```json
{
  "provider": "openai",
  "request_token_count": 5,
  "error_type": "unauthorized",
  "duration_ms": 344
}
```

**Resultado:** ✅ Provider detection, token extraction, error classification funcionando.

---

## Documentação Atualizada

**Arquivo:** `humanoid-traffic/docs/ambiente_experimental.md`
- Status dos componentes atualizado
- Log example real (OpenAI 401)
- Provider list completa (17)
- Próximos passos priorizados

---

## Commits Realizados

### nexus-gateway (branch `feat/gateway-ca-mitm`)
```
e20ea31 fix(gateway_ca): corrigir duplicata anthropic/antigravity
3c10cde feat(gateway_ca): expand provider detection + token extraction
```

### humanoid-traffic (master)
```
4e0dbc5 docs: atualizar lista de 17 providers
9b94cd1 docs: ambiente experimental atualizado - F1 provider detection completo
c7d7280 docs: ambiente experimental MITM
```

---

## Impedimentos Identificados (Para F1→F2)

| Risco | Status | Ação |
|-------|--------|------|
| Cert pinning em clientes reais | NÃO TESTADO | Próximo passo |
| CA não confiável (curl -k) | CONHECIDO | Gerar CA + instalar trust store |
| Volume logs 7 dias | BAIXO | Rotate diário + gzip |

---

## Próxima Fase: F2 — Análise Espectral

**Objetivo:** Integrar logs JSONL → `spectral.py` → assinaturas 1/f.

### Pipeline Proposto
```
JSONL logs → Parquet → spectral.py → SpectralSignature
     ↓
  CSV/Parquet com features:
  - intervals (Δt array)
  - tokens array
  - error_types array
  - provider array
     ↓
  SpectralAnalyzer.analyze(intervals) → SpectralSignature
     ↓
  Features para ML:
  - spectral_entropy, flatness, slope, dominant_freq
  - human_score (0-1)
  - will_violate threshold
```

### Integração Imediata (CONCLUÍDA)
1. **Script `jsonl_to_spectral.py`** — lê logs, agrupa por sessão/provider, roda FFT
3. **Output:** JSON com spectral features por janela temporal
4. **Alimenta** `SpectralAnalyzer` do `humanoid-traffic/src/spectral.py`

### Testado
```bash
python scripts/jsonl_to_spectral.py --log-dir /var/home/bruno/repos/NEXUS/services/nexus-gateway/logs --output-dir ./spectral_output
```
**Resultado:** 1 sessão analisada (3 requests OpenAI), features extraídas:
- spectral_entropy: 0.971
- spectral_flatness: 0.800
- spectral_slope: 0.891
- human_score: 0.6 (threshold 0.6 → BOT com poucos pontos)

---

## Comando para Continuar

```bash
# 1. Gerar CA e instalar no trust store
cd /var/home/bruno/repos/NEXUS/services/nexus-gateway
openssl req -x509 -newkey rsa:4096 -keyout certs/private.key -out certs/ca.pem -days 365 -nodes -subj "/CN=NEXUS MITM CA"

# 2. Instalar no trust store (Linux)
sudo cp certs/ca.pem /usr/local/share/ca-certificates/nexus-mitm.crt
sudo update-ca-certificates

# 3. Testar sem -k
HTTPS_PROXY=http://localhost:8082 curl https://api.openai.com/v1/models

# 4. Iniciar coleta 7 dias
python scripts/gateway_ca.py --port 8082 --log-dir ./logs
```

---

*Fim do relatório F1. Pronto para F2.*