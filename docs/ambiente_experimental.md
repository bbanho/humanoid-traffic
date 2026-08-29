# Ambiente Experimental — Captura de Tráfego MITM

## Status: FUNCIONAL ✓

O proxy MITM (`gateway_ca.py`) está operacional e capturando tráfego real.

---

## Componentes Validados

| Componente | Status | Observação |
|------------|--------|------------|
| `mitmproxy` 12.2.3 | ✓ Instalado | Via pip com binary wheel |
| `gateway_ca.py` | ✓ Executando | Porta 8082 (8080 ocupada) |
| Captura JSONL | ✓ Funcional | Log estruturado por request |
| Pass-through TLS | ✓ Funcional | `curl -k --proxy` funcionou |
| Detecção de provider | ✓ Completa | 15+ providers mapeados |
| Extração de tokens | ✓ Funcional | OpenAI, Anthropic, Gemini, OpenRouter |
| Classificação de erro | ✓ Funcional | rate_limit, forbidden, unauthorized, server_error |
| Detecção streaming | ✓ Funcional | SSE/NDJSON |

---

## Log Gerado (Exemplo Atualizado)

```json
{
  "request_id": "ca63df21-947b-4ea4-ae7f-b5127ef38e7c",
  "timestamp_start": "2026-08-29T18:58:30.382279+00:00",
  "timestamp_end": "2026-08-29T18:58:30.556686+00:00",
  "duration_ms": 175.16,
  "method": "GET",
  "url": "https://api.openai.com/v1/models",
  "host": "api.openai.com",
  "path": "/v1/models",
  "provider": "openai",
  "request_headers": {"user-agent": "curl/8.18.0", "accept": "*/*", "authorization": "Bearer fake"},
  "request_body_size": 0,
  "request_token_count": null,
  "response_status": 401,
  "response_headers": {...},
  "response_body_size": 233,
  "response_token_count": null,
  "response_total_tokens": null,
  "error_type": "unauthorized",
  "is_streaming": false
}
```

---

## Requisitos Procedentes (F1 — Captura Baseline)

### 1. Infraestrutura
- [x] Proxy MITM com CA custom (mitmproxy)
- [x] Log JSONL estruturado por request
- [x] Pass-through TLS sem modificação
- [x] Extração de metadados: headers, body size, latency, status

### 2. Detecção de Provider (Concluído)
- [x] Mapear hosts conhecidos: `api.anthropic.com`, `api.openai.com`, `generativelanguage.googleapis.com`, `api.deepseek.com`, `api.groq.com`, `api.x.ai`, `api.mistral.ai`, `api.perplexity.ai`, `api.cohere.ai`, `api.together.xyz`, `api.fireworks.ai`, `openrouter.ai`, `chat.openai.com`, `gemini.google.com`, `poe.com`
- [x] Extrair token counts de responses (OpenAI, Anthropic, Gemini, OpenRouter formats)
- [x] Classificar erro types: 429 (rate_limit), 403 (forbidden), 401 (unauthorized), 500, 502, 503
- [x] Detectar streaming (SSE/NDJSON via content-type)
- [x] Extrair request_token_count via max_tokens

### 3. Coleta de Baseline (7 dias)
- [ ] Executar clientes legítimos via proxy:
  - `HTTPS_PROXY=http://localhost:8082 claude-code ...`
  - `HTTPS_PROXY=http://localhost:8082 python -m openai ...`
  - `HTTPS_PROXY=http://localhost:8082 gemini-cli ...`
- [ ] Mínimo 10.000 requests por perfil
- [ ] Segmentar por: provedor, tipo de tarefa, horário

### 4. Armazenamento e Análise
- [ ] Logs em `/var/home/bruno/repos/NEXUS/services/nexus-gateway/logs/`
- [ ] Pipeline: JSONL → Parquet → Análise espectral (`spectral.py`)
- [ ] Integração com `humanoid-traffic/src/spectral.py`

---

## Impedimentos Conceituais Identificados

| Risco | Severidade | Mitigação |
|-------|------------|-----------|
| Provider detecta MITM via cert pinning | ALTA | Testar com clientes reais; alguns fazem pinning |
| Cliente rejeita CA não confiável | MÉDIA | Instalar CA no trust store do sistema/cliente |
| Volume de logs (7 dias × 10k reqs) | BAIXA | Rotate logs diários; compressão gzip |
| Correlação request→response em streaming | MÉDIA | Buffer por request_id; handle SSE |

---

## Aproveitamento em Outro Campo (Se F1 Falhar)

Se a captura de tráfego de provedores reais for bloqueada (cert pinning, detecção de MITM), a pesquisa **não é perdida**:

1. **Modelo Espectral (`spectral.py`)** — Independente de fonte de dados; aplica-se a qualquer série temporal
2. **Simulador Humanoide (`generator.py`)** — Gera tráfego sintético com assinatura 1/f para testes
3. **Detetor Híbrido (`detector.py`)** — Classifica padrões sem precisar de dados reais
4. **Otimizador de Throughput (`optimizer.py`)** — Calcula limites teóricos

Esses componentes podem ser usados para:
- **Análise de tráfego de rede** (DDoS detection, anomaly detection)
- **Modelagem de comportamento de usuário** (UX, product analytics)
- **Sistemas de rate limiting adaptativo** (API gateways genéricos)
- **Pesquisa em séries temporais financeiras** (mesma matemática 1/f)

---

## Próximos Passos

1. **Instalar CA no cliente** (evitar `curl -k`) — gerar certificado e adicionar ao trust store
2. **Executar coleta de 7 dias** com clientes reais:
   - `HTTPS_PROXY=http://localhost:8082 claude-code ...`
   - `HTTPS_PROXY=http://localhost:8082 python -m openai ...`
   - `HTTPS_PROXY=http://localhost:8082 gemini-cli ...`
3. **Mínimo 10.000 requests por perfil** — segmentar por provedor, tipo de tarefa, horário
4. **Integrar com `humanoid-traffic`** para análise espectral automática:
   - JSONL → Parquet → `spectral.py` → assinaturas 1/f
5. **Testar cert pinning** — clientes reais podem rejeitar MITM

---

## Comandos de Operação

```bash
# Iniciar proxy (porta 8082)
cd /var/home/bruno/repos/NEXUS/services/nexus-gateway
python scripts/gateway_ca.py --port 8082 --log-dir ./logs

# Usar cliente via proxy
export HTTPS_PROXY=http://localhost:8082
export HTTP_PROXY=http://localhost:8082
# Adicionar CA ao trust store se necessário

# Ver logs
cat logs/*.jsonl | jq .

# Parar
pkill -f gateway_ca.py
```