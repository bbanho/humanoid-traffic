# HANDOFF — Humanoid Traffic / NEXUS Gateway MITM
**Data:** 2026-08-29
**Sessão:** Captura de Tráfego + Análise Espectral + CA/Pinning
**Estado:** F1 + F2 concluídos, F3 (Pinning Real) pendente

---

## Resumo Executivo

Implementamos pipeline completo de **captura → análise espectral** para tráfego de APIs de IA, com proxy MITM funcional, detecção de 17 providers, extração de tokens, classificação de erros, e pipeline FFT para features espectrais.

---

## Entregáveis

### 1. Repositório `humanoid-traffic` (master)
```
humanoid-traffic/
├── README.md                    # Visão geral
├── docs/
│   ├── roteiro_abntex.tex       # Roteiro metodológico ABNT2
│   ├── referencias.bib          # Bibliografia
│   ├── ambiente_experimental.md # Docs do gateway MITM
│   ├── relatorio_f1.md          # Relatório F1+F2 completo
│   └── ca_cert_pinning.md       # CA + pinning docs
├── src/
│   ├── spectral.py              # SpectralAnalyzer (FFT, entropy, flatness, slope)
│   └── __init__.py
├── scripts/
│   ├── jsonl_to_spectral.py     # Pipeline JSONL → Spectral Features
│   └── demo_spectral.py         # Demo isolada
└── spectral_output/             # Outputs de teste
```

### 2. Repositório `nexus-gateway` (branch `feat/gateway-ca-mitm`)
```
services/nexus-gateway/
├── scripts/gateway_ca.py        # Proxy MITM (300 linhas)
├── certs/
│   ├── ca.pem                   # Certificado público
│   └── private.key              # Chave privada
├── logs/                        # JSONL captured
└── pyproject.toml               # + mitmproxy 12.2.3
```

---

## Componentes Validados

| Componente | Status | Detalhes |
|------------|--------|----------|
| **Gateway MITM** | ✅ | Porta 8082, pass-through TLS, JSONL logging |
| **Provider Detection** | ✅ | 17 providers únicos (OpenAI, Anthropic, Gemini, DeepSeek, Groq, etc.) |
| **Token Extraction** | ✅ | 4 formats: OpenAI, Anthropic, Gemini, OpenRouter |
| **Error Classification** | ✅ | 6 tipos: rate_limit, forbidden, unauthorized, server_error, bad_gateway, service_unavailable |
| **Streaming Detection** | ✅ | SSE/NDJSON via content-type |
| **Spectral Analysis** | ✅ | FFT + entropy, flatness, slope, dominant_freq |
| **Pipeline JSONL→Spectral** | ✅ | Session grouping, feature extraction, human_score |
| **CA Certificate** | ✅ | RSA 4096, 365d, via REQUESTS_CA_BUNDLE (sem sudo) |
| **Pinning Docs** | ✅ | Tabela de clientes, mitigations |

---

## Validação Experimental

### Gateway MITM
```bash
# Testado com:
curl -k https://httpbin.org/get --proxy http://localhost:8082     # ✅
curl -k https://api.openai.com/v1/models --proxy http://localhost:8082  # ✅ (401 captured)
curl -k https://api.openai.com/v1/chat/completions --proxy ...     # ✅ max_tokens=5 extracted
```

### Spectral Pipeline
```bash
python scripts/jsonl_to_spectral.py \
  --log-dir /var/home/bruno/repos/NEXUS/services/nexus-gateway/logs \
  --output-dir ./spectral_output

# Output: spectral_features_*.json com features:
# - spectral_entropy: 0.971
# - spectral_flatness: 0.800
# - spectral_slope: 0.891
# - human_score: 0.6 (BOT com 3 requests apenas)
```

### CA Certificate
```bash
# Gerado:
openssl req -x509 -newkey rsa:4096 -keyout certs/private.key -out certs/ca.pem -days 365 -nodes -subj "/CN=NEXUS MITM CA"

# Testado via REQUESTS_CA_BUNDLE (sem sudo):
export REQUESTS_CA_BUNDLE=/var/home/bruno/repos/NEXUS/services/nexus-gateway/certs/ca.pem
curl https://httpbin.org/get --proxy http://localhost:8082  # ✅ sem -k
```

---

## Impedimentos Conhecidos

| Risco | Status | Próxima Ação |
|-------|--------|--------------|
| **Cert Pinning em clientes reais** | NÃO TESTADO | Testar com claude-code, openai, gemini CLI reais |
| **Volume logs 7 dias** | BAIXO | Rotate diário + gzip (planejado) |
| **Token extraction em streaming** | PARCIAL | Precisa handle SSE chunks |

---

## Próximos Passos (Prioridade)

### 1. Testar Cert Pinning Real (CRÍTICO)
```bash
export REQUESTS_CA_BUNDLE=/var/home/bruno/repos/NEXUS/services/nexus-gateway/certs/ca.pem
export HTTPS_PROXY=http://localhost:8082
export HTTP_PROXY=http://localhost:8082

# Testar clientes reais (precisa ter instalado+autenticado):
claude-code --version          # ou comando real
python -c "import openai; print(openai.OpenAI().models.list())"
gemini --help
```

**Se falhar pinning:** Documentar qual cliente falhou, tentar workaround (custom client sem pinning).

### 2. Coleta Baseline 7 Dias
```bash
# Iniciar proxy
python scripts/gateway_ca.py --port 8082 --log-dir ./logs

# Configurar clientes reais via proxy
export REQUESTS_CA_BUNDLE=/path/to/ca.pem
export HTTPS_PROXY=http://localhost:8082
# ... usar clientes normalmente por 7 dias
```

**Meta:** 10k+ requests por perfil (developer, casual, power_user)

### 3. Análise Espectral Completa
- Rodar `jsonl_to_spectral.py` nos logs de 7 dias
- Calcular assinaturas 1/f por perfil
- Validar human_score vs ground truth

### 4. Modelo Preditivo
- Treinar classificador com features espectrais
- Definir thresholds ótimos de operação
- Integrar no key_pool_manager

---

## Comandos Úteis

```bash
# Iniciar proxy MITM
cd /var/home/bruno/repos/NEXUS/services/nexus-gateway
python scripts/gateway_ca.py --port 8082 --log-dir ./logs

# Ver logs
cat logs/*.jsonl | jq .

# Processar espectral
cd /home/bruno/repos/humanoid-traffic
python scripts/jsonl_to_spectral.py \
  --log-dir /var/home/bruno/repos/NEXUS/services/nexus-gateway/logs \
  --output-dir ./spectral_output

# Testar cliente real
export REQUESTS_CA_BUNDLE=/var/home/bruno/repos/NEXUS/services/nexus-gateway/certs/ca.pem
export HTTPS_PROXY=http://localhost:8082
# ... comando do cliente
```

---

## Arquivos-chave para Continuidade

| Arquivo | Localização | Função |
|---------|-------------|--------|
| `gateway_ca.py` | `nexus-gateway/scripts/` | Proxy MITM principal |
| `spectral.py` | `humanoid-traffic/src/` | FFT + métricas espectrais |
| `jsonl_to_spectral.py` | `humanoid-traffic/scripts/` | Pipeline JSONL → Features |
| `ambiente_experimental.md` | `humanoid-traffic/docs/` | Docs do gateway |
| `relatorio_f1.md` | `humanoid-traffic/docs/` | Relatório completo F1+F2 |
| `ca_cert_pinning.md` | `humanoid-traffic/docs/` | CA + pinning guide |
| `roteiro_abntex.tex` | `humanoid-traffic/docs/` | Roteiro ABNT2 |

---

## Branches Git

| Repo | Branch | Commit |
|------|--------|--------|
| `nexus-gateway` | `feat/gateway-ca-mitm` | `e20ea31` (fix anthropic) |
| `humanoid-traffic` | `master` | `31c11ba` (ca_cert_pinning) |

---

## Contato / Contexto

- **Máquina:** neural-node (Bluefin, 8GB, GTX 1660 SUPER)
- **Rede:** tailscale `100.121.172.4`
- **NEXUS stack:** 6 containers (postgres, qdrant, ollama, engine, mcp, gateway)
- **Ollama:** qwen2.5-coder:7b (~33 tok/s), nomic-embed-text

---

*Fim do handoff. Próxima sessão deve iniciar no teste de cert pinning com clientes reais.*